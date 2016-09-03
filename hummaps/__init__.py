from flask import Flask
from flask.ext.bootstrap import Bootstrap
from flask.ext.login import LoginManager

app = Flask(__name__)

# configuration
DEBUG = True
DATABASE_URL = r'postgresql+psycopg2://hummaps:#dq8536*^*@localhost:5432/ec2-user'
DATABASE_TABLE_ARGS = {'schema': 'hummaps'}
SECRET_KEY = b'\xff\xe9\xbaZ\x8ao\xbf\xf5W\x00\xa0T\x05Rd\xc0u\xca\x00\xc2\xa9\xebnM'
RECAPTCHA_PARAMETERS = {'render': 'onload'}
RECAPTCHA_DATA_ATTRS = {'theme': 'dark', 'size': 'normal'}
RECAPTCHA_PUBLIC_KEY = '6Lc3iBkTAAAAAACduP62sPp1Zq6iD6wDES0iIVrE'
RECAPTCHA_PRIVATE_KEY = '6Lc3iBkTAAAAAJmOqU8GF4LLxQQvSIwnd65JgoWF'

# app.config.from_envvar('FLASKAPP_CONFIG', silent=False)
app.config.from_object(__name__)

# Bootstrap extension
bootstrap = Bootstrap(app)

# Login manager extension
login_manager = LoginManager()
login_manager.session_protection = 'strong'
login_manager.login_view = 'login'
login_manager.init_app(app)

import hummaps.views

from hummaps.database import db_session

@app.before_request
def before_request():
    pass

@app.after_request
def after_request(response):
    return response

@app.teardown_request
def teardown_request(exception):
    pass

@app.teardown_appcontext
def teardown_appcontext(exception):
    db_session.remove()
