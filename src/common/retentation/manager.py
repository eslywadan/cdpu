# src/common/retention/manager.py
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from enum import Enum
import asyncio
import logging

logger = logging.getLogger(__name__)

class DataCategory(Enum):
    """Data categories for retention"""
    EVENTS = "events"
    LOGS = "logs"
    AUDIT = "audit"
    METRICS = "metrics"
    TASKS = "tasks"
    SESSIONS = "sessions"
    CACHE = "cache"

class StorageTier(Enum):
    """Storage tiers"""
    HOT = "hot"      # Fast, expensive storage
    WARM = "warm"    # Medium speed, compressed
    COLD = "cold"    # Slow, cheap storage (S3, etc.)
    ARCHIVE = "archive"  # Long-term archive

@dataclass
class RetentionPolicy:
    """Retention policy configuration"""
    category: DataCategory
    hot_duration: timedelta
    warm_duration: timedelta
    cold_duration: timedelta
    archive_duration: Optional[timedelta]
    delete_after: Optional[timedelta]
    compression_enabled: bool = True
    encryption_enabled: bool = False
    
    def get_tier_for_age(self, age: timedelta) -> StorageTier:
        """Get storage tier based on data age"""
        
        if age < self.hot_duration:
            return StorageTier.HOT
        elif age < self.warm_duration:
            return StorageTier.WARM
        elif age < self.cold_duration:
            return StorageTier.COLD
        elif self.archive_duration and age < self.archive_duration:
            return StorageTier.ARCHIVE
        else:
            return None  # Should be deleted

class RetentionManager:
    """Manages data retention policies"""
    
    def __init__(self,
                 db_engine,
                 s3_client=None,
                 redis_client=None):
        
        self.db_engine = db_engine
        self.s3_client = s3_client
        self.redis = redis_client
        
        self.policies: Dict[DataCategory, RetentionPolicy] = {}
        self._setup_default_policies()
        
        self._running = False
        self._tasks = []
    
    def _setup_default_policies(self):
        """Setup default retention policies"""
        
        # Events retention
        self.policies[DataCategory.EVENTS] = RetentionPolicy(
            category=DataCategory.EVENTS,
            hot_duration=timedelta(days=30),
            warm_duration=timedelta(days=90),
            cold_duration=timedelta(days=365),
            archive_duration=timedelta(days=730),  # 2 years
            delete_after=timedelta(days=2555),  # 7 years
            compression_enabled=True
        )
        
        # Logs retention
        self.policies[DataCategory.LOGS] = RetentionPolicy(
            category=DataCategory.LOGS,
            hot_duration=timedelta(days=7),
            warm_duration=timedelta(days=30),
            cold_duration=timedelta(days=90),
            archive_duration=None,
            delete_after=timedelta(days=180),
            compression_enabled=True
        )
        
        # Audit retention (compliance)
        self.policies[DataCategory.AUDIT] = RetentionPolicy(
            category=DataCategory.AUDIT,
            hot_duration=timedelta(days=90),
            warm_duration=timedelta(days=365),
            cold_duration=timedelta(days=2555),
            archive_duration=None,
            delete_after=None,  # Never delete
            compression_enabled=True,
            encryption_enabled=True
        )
        
        # Metrics retention
        self.policies[DataCategory.METRICS] = RetentionPolicy(
            category=DataCategory.METRICS,
            hot_duration=timedelta(days=7),
            warm_duration=timedelta(days=30),
            cold_duration=timedelta(days=90),
            archive_duration=None,
            delete_after=timedelta(days=365),
            compression_enabled=True
        )
    
    async def start(self):
        """Start retention manager"""
        
        self._running = True
        
        # Start retention tasks
        self._tasks = [
            asyncio.create_task(self._retention_loop()),
            asyncio.create_task(self._compression_loop()),
            asyncio.create_task(self._archival_loop()),
            asyncio.create_task(self._deletion_loop())
        ]
        
        logger.info("Retention manager started")
    
    async def stop(self):
        """Stop retention manager"""
        
        self._running = False
        
        for task in self._tasks:
            task.cancel()
        
        await asyncio.gather(*self._tasks, return_exceptions=True)
        
        logger.info("Retention manager stopped")
    
    async def _retention_loop(self):
        """Main retention processing loop"""
        
        while self._running:
            try:
                for category, policy in self.policies.items():
                    await self._process_retention(category, policy)
                
                # Run daily
                await asyncio.sleep(86400)
                
            except Exception as e:
                logger.error(f"Retention error: {e}")
                await asyncio.sleep(3600)
    
    async def _process_retention(self,
                                category: DataCategory,
                                policy: RetentionPolicy):
        """Process retention for a data category"""
        
        logger.info(f"Processing retention for {category.value}")
        
        # Get data statistics
        stats = await self._get_data_statistics(category)
        
        # Move data between tiers
        await self._migrate_to_warm(category, policy, stats)
        await self._migrate_to_cold(category, policy, stats)
        
        if policy.archive_duration:
            await self._migrate_to_archive(category, policy, stats)
        
        if policy.delete_after:
            await self._delete_expired(category, policy, stats)
    
    async def _get_data_statistics(self,
                                  category: DataCategory) -> Dict:
        """Get data statistics for category"""
        
        with self.db_engine.connect() as conn:
            # Get data age distribution
            if category == DataCategory.EVENTS:
                result = conn.execute(text("""
                    SELECT 
                        COUNT(*) as count,
                        MIN(timestamp) as oldest,
                        MAX(timestamp) as newest,
                        pg_size_pretty(pg_total_relation_size('events')) as size
                    FROM events
                """))
            elif category == DataCategory.LOGS:
                result = conn.execute(text("""
                    SELECT 
                        COUNT(*) as count,
                        MIN(created_at) as oldest,
                        MAX(created_at) as newest,
                        pg_size_pretty(pg_total_relation_size('logs')) as size
                    FROM logs
                """))
            # Add more categories as needed
            
            stats = dict(result.fetchone())
            
        return stats
    
    async def _migrate_to_warm(self,
                              category: DataCategory,
                              policy: RetentionPolicy,
                              stats: Dict):
        """Migrate data to warm tier"""
        
        cutoff_date = datetime.utcnow() - policy.hot_duration
        
        with self.db_engine.connect() as conn:
            if category == DataCategory.EVENTS:
                # Move to partitioned warm table
                conn.execute(text("""
                    INSERT INTO events_warm
                    SELECT * FROM events
                    WHERE timestamp < :cutoff
                    ON CONFLICT DO NOTHING
                """), {'cutoff': cutoff_date})
                
                # Compress if enabled
                if policy.compression_enabled:
                    conn.execute(text("""
                        ALTER TABLE events_warm 
                        SET (compression = zstd)
                    """))
                
                # Delete from hot table
                conn.execute(text("""
                    DELETE FROM events
                    WHERE timestamp < :cutoff
                """), {'cutoff': cutoff_date})
                
                conn.commit()
        
        logger.info(f"Migrated {category.value} data to warm tier")
    
    async def _migrate_to_cold(self,
                              category: DataCategory,
                              policy: RetentionPolicy,
                              stats: Dict):
        """Migrate data to cold tier (S3)"""
        
        if not self.s3_client:
            return
        
        cutoff_date = datetime.utcnow() - policy.warm_duration
        
        with self.db_engine.connect() as conn:
            if category == DataCategory.EVENTS:
                # Export to S3
                result = conn.execute(text("""
                    SELECT * FROM events_warm
                    WHERE timestamp < :cutoff
                    LIMIT 10000
                """), {'cutoff': cutoff_date})
                
                records = result.fetchall()
                
                if records:
                    # Convert to Parquet format
                    import pyarrow as pa
                    import pyarrow.parquet as pq
                    
                    df = pd.DataFrame(records)
                    table = pa.Table.from_pandas(df)
                    
                    # Write to S3
                    s3_key = f"cold/{category.value}/{datetime.utcnow().date()}.parquet"
                    
                    buffer = io.BytesIO()
                    pq.write_table(table, buffer, compression='snappy')
                    
                    self.s3_client.put_object(
                        Bucket='cdpu-cold-storage',
                        Key=s3_key,
                        Body=buffer.getvalue()
                    )
                    
                    # Delete from warm table
                    conn.execute(text("""
                        DELETE FROM events_warm
                        WHERE timestamp < :cutoff
                    """), {'cutoff': cutoff_date})
                    
                    conn.commit()
        
        logger.info(f"Migrated {category.value} data to cold tier")
    
    async def _compression_loop(self):
        """Compress data in warm tier"""
        
        while self._running:
            try:
                for category, policy in self.policies.items():
                    if policy.compression_enabled:
                        await self._compress_data(category)
                
                # Run every 6 hours
                await asyncio.sleep(21600)
                
            except Exception as e:
                logger.error(f"Compression error: {e}")
                await asyncio.sleep(3600)
    
    async def _compress_data(self, category: DataCategory):
        """Compress data for category"""
        
        with self.db_engine.connect() as conn:
            if category == DataCategory.EVENTS:
                # PostgreSQL automatic compression
                conn.execute(text("""
                    ALTER TABLE events_warm SET (
                        compression = zstd,
                        compression_level = 3
                    )
                """))
                
                # Vacuum to apply compression
                conn.execute(text("VACUUM FULL events_warm"))
        
        logger.info(f"Compressed {category.value} data")
    
    async def _archival_loop(self):
        """Archive old data"""
        
        while self._running:
            try:
                for category, policy in self.policies.items():
                    if policy.archive_duration:
                        await self._archive_data(category, policy)
                
                # Run weekly
                await asyncio.sleep(604800)
                
            except Exception as e:
                logger.error(f"Archival error: {e}")
                await asyncio.sleep(86400)
    
    async def _deletion_loop(self):
        """Delete expired data"""
        
        while self._running:
            try:
                for category, policy in self.policies.items():
                    if policy.delete_after:
                        await self._delete_expired_data(category, policy)
                
                # Run daily
                await asyncio.sleep(86400)
                
            except Exception as e:
                logger.error(f"Deletion error: {e}")
                await asyncio.sleep(3600)
    
    async def _delete_expired_data(self,
                                  category: DataCategory,
                                  policy: RetentionPolicy):
        """Delete expired data"""
        
        cutoff_date = datetime.utcnow() - policy.delete_after
        
        with self.db_engine.connect() as conn:
            if category == DataCategory.LOGS:
                deleted = conn.execute(text("""
                    DELETE FROM logs
                    WHERE created_at < :cutoff
                    RETURNING COUNT(*)
                """), {'cutoff': cutoff_date})
                
                count = deleted.scalar()
                conn.commit()
                
                logger.info(f"Deleted {count} expired {category.value} records")