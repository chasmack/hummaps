from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, ForeignKey

from werkzeug.security import generate_password_hash, check_password_hash
from flask.ext.login import UserMixin

from hummaps import app, login_manager

engine = create_engine(app.config['DATABASE_URL'])
db_session = scoped_session(
    sessionmaker(autocommit=False, autoflush=False, bind=engine))

Base = declarative_base()
if 'schema' in app.config['DATABASE_TABLE_ARGS']:
    Base.metadata.schema = app.config['DATABASE_TABLE_ARGS']['schema']
Base.query = db_session.query_property()


def init_db():
    Base.metadata.create_all(bind=engine)
