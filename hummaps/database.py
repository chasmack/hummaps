from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base

from hummaps import app

engine = create_engine(app.config['DATABASE_URL'], echo=False)
db_session = scoped_session(
    sessionmaker(autocommit=False, autoflush=False, bind=engine))

Base = declarative_base()
if 'schema' in app.config['DATABASE_TABLE_ARGS']:
    Base.metadata.schema = app.config['DATABASE_TABLE_ARGS']['schema']
Base.query = db_session.query_property()
