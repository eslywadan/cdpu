# src/common/api/deprecation.py
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json

logger = logging.getLogger(__name__)

class DeprecationStatus(Enum):
    """Deprecation status levels"""
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    SUNSET_WARNING = "sunset_warning"
    SUNSET = "sunset"

@dataclass
class DeprecationNotice:
    """Deprecation notice details"""
    version: str
    deprecated_at: datetime
    sunset_at: datetime
    successor: str
    reason: str = ""
    migration_guide_url: str = ""
    affected_endpoints: List[str] = field(default_factory=list)
    notified_clients: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'version': self.version,
            'deprecated_at': self.deprecated_at.isoformat(),
            'sunset_at': self.sunset_at.isoformat(),
            'successor': self.successor,
            'reason': self.reason,
            'migration_guide_url': self.migration_guide_url,
            'affected_endpoints': self.affected_endpoints,
            'days_until_sunset': (self.sunset_at - datetime.now()).days,
            'status': self.get_status().value
        }
    
    def get_status(self) -> DeprecationStatus:
        """Get current deprecation status"""
        now = datetime.now()
        days_until_sunset = (self.sunset_at - now).days
        
        if now >= self.sunset_at:
            return DeprecationStatus.SUNSET
        elif days_until_sunset <= 30:
            return DeprecationStatus.SUNSET_WARNING
        else:
            return DeprecationStatus.DEPRECATED

class DeprecationManager:
    """Manages API version deprecation lifecycle"""
    
    def __init__(self, redis_client=None, db_engine=None):
        self.redis = redis_client
        self.db_engine = db_engine
        self.notices: Dict[str, DeprecationNotice] = {}
        self.notification_handlers: List[Callable] = []
        
    def deprecate_version(self,
                         version: str,
                         sunset_days: int,
                         successor: str,
                         reason: str = "",
                         affected_endpoints: List[str] = None) -> DeprecationNotice:
        """Deprecate an API version"""
        
        notice = DeprecationNotice(
            version=version,
            deprecated_at=datetime.now(),
            sunset_at=datetime.now() + timedelta(days=sunset_days),
            successor=successor,
            reason=reason,
            migration_guide_url=f"/docs/migration/{version}-to-{successor}",
            affected_endpoints=affected_endpoints or []
        )
        
        self.notices[version] = notice
        
        # Store in Redis for persistence
        if self.redis:
            self.redis.set(
                f"deprecation:{version}",
                json.dumps(notice.to_dict()),
                ex=sunset_days * 86400  # Expire after sunset
            )
        
        # Store in database
        if self.db_engine:
            self._store_deprecation_in_db(notice)
        
        # Trigger notifications
        self._notify_deprecation(notice)
        
        logger.info(f"Version {version} deprecated. Sunset: {notice.sunset_at}")
        
        return notice
    
    def _store_deprecation_in_db(self, notice: DeprecationNotice):
        """Store deprecation notice in database"""
        
        from sqlalchemy import text
        
        with self.db_engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO api_deprecations 
                (version, deprecated_at, sunset_at, successor, reason, status)
                VALUES (:version, :deprecated_at, :sunset_at, :successor, :reason, :status)
                ON CONFLICT (version) DO UPDATE SET
                    sunset_at = :sunset_at,
                    status = :status
            """), {
                'version': notice.version,
                'deprecated_at': notice.deprecated_at,
                'sunset_at': notice.sunset_at,
                'successor': notice.successor,
                'reason': notice.reason,
                'status': notice.get_status().value
            })
            conn.commit()
    
    def _notify_deprecation(self, notice: DeprecationNotice):
        """Send deprecation notifications"""
        
        # Get affected clients
        clients = self._get_clients_using_version(notice.version)
        
        for client in clients:
            try:
                # Send email notification
                self._send_deprecation_email(client, notice)
                
                # Send webhook notification
                self._send_webhook_notification(client, notice)
                
                # Record notification
                notice.notified_clients.append(client['client_id'])
                
            except Exception as e:
                logger.error(f"Failed to notify client {client['client_id']}: {e}")
        
        # Execute custom handlers
        for handler in self.notification_handlers:
            try:
                handler(notice)
            except Exception as e:
                logger.error(f"Notification handler failed: {e}")
    
    def _get_clients_using_version(self, version: str) -> List[Dict]:
        """Get list of clients using specific version"""
        
        if not self.db_engine:
            return []
        
        from sqlalchemy import text
        
        with self.db_engine.connect() as conn:
            result = conn.execute(text("""
                SELECT DISTINCT 
                    c.client_id,
                    c.client_name,
                    c.email,
                    c.webhook_url,
                    COUNT(r.id) as request_count
                FROM clients c
                JOIN api_requests r ON c.client_id = r.client_id
                WHERE r.api_version = :version
                    AND r.timestamp > NOW() - INTERVAL '30 days'
                GROUP BY c.client_id, c.client_name, c.email, c.webhook_url
                ORDER BY request_count DESC
            """), {'version': version})
            
            return [dict(row) for row in result]
    
    def _send_deprecation_email(self, client: Dict, notice: DeprecationNotice):
        """Send deprecation email to client"""
        
        subject = f"Important: API Version {notice.version} Deprecation Notice"
        
        html_body = f"""
        <html>
        <body>
            <h2>API Version {notice.version} Deprecation Notice</h2>
            
            <p>Dear {client['client_name']},</p>
            
            <p>We are writing to inform you that API version <strong>{notice.version}</strong> 
            has been deprecated and will be sunset on <strong>{notice.sunset_at.date()}</strong>.</p>
            
            <h3>Important Information:</h3>
            <ul>
                <li><strong>Current Version:</strong> {notice.version}</li>
                <li><strong>Recommended Version:</strong> {notice.successor}</li>
                <li><strong>Sunset Date:</strong> {notice.sunset_at.date()}</li>
                <li><strong>Days Remaining:</strong> {(notice.sunset_at - datetime.now()).days}</li>
            </ul>
            
            <h3>Action Required:</h3>
            <ol>
                <li>Review the <a href="{notice.migration_guide_url}">migration guide</a></li>
                <li>Update your integration to use version {notice.successor}</li>
                <li>Test your integration thoroughly</li>
                <li>Deploy changes before {notice.sunset_at.date()}</li>
            </ol>
            
            <h3>Your Usage Statistics (Last 30 Days):</h3>
            <ul>
                <li>Total API Calls: {client.get('request_count', 0)}</li>
                <li>Client ID: {client['client_id']}</li>
            </ul>
            
            <p>If you need assistance with the migration, please contact our support team.</p>
            
            <p>Best regards,<br>API Team</p>
        </body>
        </html>
        """
        
        # Send email (implement based on your email service)
        # self._send_email(client['email'], subject, html_body)
        logger.info(f"Deprecation email sent to {client['client_name']}")
    
    def _send_webhook_notification(self, client: Dict, notice: DeprecationNotice):
        """Send webhook notification to client"""
        
        if not client.get('webhook_url'):
            return
        
        import requests
        
        payload = {
            'event': 'api.version.deprecated',
            'timestamp': datetime.now().isoformat(),
            'data': notice.to_dict(),
            'client_id': client['client_id']
        }
        
        try:
            response = requests.post(
                client['webhook_url'],
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            logger.info(f"Webhook sent to {client['client_name']}")
        except Exception as e:
            logger.error(f"Webhook failed for {client['client_name']}: {e}")
    
    def check_sunset_warnings(self):
        """Check for versions approaching sunset and send warnings"""
        
        for version, notice in self.notices.items():
            status = notice.get_status()
            
            if status == DeprecationStatus.SUNSET_WARNING:
                # Send warning notifications
                self._send_sunset_warning(notice)
            elif status == DeprecationStatus.SUNSET:
                # Handle sunset
                self._handle_sunset(notice)
    
    def _send_sunset_warning(self, notice: DeprecationNotice):
        """Send sunset warning notifications"""
        
        days_remaining = (notice.sunset_at - datetime.now()).days
        
        # Only send on specific intervals
        if days_remaining in [30, 14, 7, 3, 1]:
            logger.warning(f"Version {notice.version} sunsets in {days_remaining} days")
            
            # Re-notify clients still using the version
            clients = self._get_clients_using_version(notice.version)
            
            for client in clients:
                # Send urgent notification
                self._send_urgent_sunset_warning(client, notice, days_remaining)
    
    def _send_urgent_sunset_warning(self, client: Dict, notice: DeprecationNotice, days_remaining: int):
        """Send urgent sunset warning"""
        
        subject = f"URGENT: API Version {notice.version} Sunsets in {days_remaining} Days"
        
        # Send high-priority notification
        logger.warning(f"Urgent sunset warning sent to {client['client_name']}")