from sqlalchemy import create_engine, Column, Integer, String, Text, PrimaryKeyConstraint, Index
from sqlalchemy.orm import declarative_base, sessionmaker
from dpcm.database_config import postgresql_config

# postgres connection uri
DATABASE_URL = postgresql_config(env="ci-dev")

# SQLAlchemy Setup 
Base = declarative_base()

class Account(Base):
    __tablename__ = 'account'
 
    SOURCE = Column(Text)
    CLIENT_ID = Column(Text)
    PASSWORD = Column(Text)
    TYPE = Column(Integer)
    EXPIRE = Column(Text)
    PERMISSION = Column(Text)
    OBSOLETE = Column(Integer)
    OWNER_USER_ID = Column(Text)
    CREATE_DTTM = Column(Text)
    REGISTRY = Column(String)
    BIND_ROLE = Column(Text)
    BIND_GROUP = Column(Text)
    
    __table_args__ = (
        PrimaryKeyConstraint('SOURCE', 'CLIENT_ID'),
        Index('idx_source', 'SOURCE'),
    )
    
    # -- Engine and Table Creation ---
    engine = create_engine(DATABASE_URL, echo=True) # echo=True to log SQL statements
        
    @classmethod
    def drop_table(cls):
        cls.metadata.drop_all(cls.engine)
        
    @classmethod
    def create_table(cls):
        cls.metadata.create_all(cls.engine)
    
    @classmethod
    def create_session(cls):    
        # --- optionall: Create a session --
        SessionLocal = sessionmaker(bind=cls.engine)
        session = SessionLocal()
        return session
 

    