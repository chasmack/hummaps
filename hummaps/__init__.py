from flask import Flask

app = Flask(__name__)

# configuration
DEBUG = False
DATABASE_URL = r'postgresql+psycopg2://hummaps:g712X$@localhost:5432/production'
DATABASE_TABLE_ARGS = {'schema': 'hummaps'}
SECRET_KEY = b'\xff\xe9\xbaZ\x8ao\xbf\xf5W\x00\xa0T\x05Rd\xc0u\xca\x00\xc2\xa9\xebnM'
RECAPTCHA_PARAMETERS = {'render': 'onload'}
RECAPTCHA_DATA_ATTRS = {'theme': 'dark', 'size': 'normal'}
RECAPTCHA_PUBLIC_KEY = '6Lc3iBkTAAAAAACduP62sPp1Zq6iD6wDES0iIVrE'
RECAPTCHA_PRIVATE_KEY = '6Lc3iBkTAAAAAJmOqU8GF4LLxQQvSIwnd65JgoWF'

# Mazimum file upload size
MAX_CONTENT_LENGTH = 2.5 * 1024 * 1024

# Default cache control lifetime (seconds)
SEND_FILE_MAX_AGE_DEFAULT = 604800

# app.config.from_envvar('FLASKAPP_CONFIG', silent=False)
app.config.from_object(__name__)

import hummaps.views

from hummaps.database import db_session

@app.before_request
def before_request():
    pass

@app.after_request
def after_request(resp):
    if resp.mimetype == 'text/html':
        resp.cache_control.no_store = True
        resp.cache_control.no_cache = True
    return resp

@app.teardown_request
def teardown_request(exception):
    pass

@app.teardown_appcontext
def teardown_appcontext(exception):
    db_session.remove()
