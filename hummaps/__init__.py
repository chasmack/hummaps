from flask import Flask
from flask_bootstrap import Bootstrap

from datetime import datetime, timedelta

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

VERSION = '17.12.07'

MAX_AGE = {
    'text/html': 0,
    'text/css': 604800,
    'application/javascript': 604800,
    'application/octet-stream': 604800
}

# app.config.from_envvar('FLASKAPP_CONFIG', silent=False)
app.config.from_object(__name__)

# Bootstrap extension
bootstrap = Bootstrap(app)

import hummaps.views

from hummaps.database import db_session

@app.before_request
def before_request():
    pass

@app.after_request
def after_request(response):
    # Cache control
    if response.mimetype in MAX_AGE:
        max_age = MAX_AGE[response.mimetype]
        if max_age > 0:
            response.cache_control.max_age = max_age
            expires = (datetime.utcnow() + timedelta(seconds=max_age))
            response.headers['Expires'] = expires.strftime('%a, %d %b %Y %H:%M:%S GMT')
        else:
            response.cache_control.no_cache = True
            response.cache_control.no_store = True
    return response

@app.teardown_request
def teardown_request(exception):
    pass

@app.teardown_appcontext
def teardown_appcontext(exception):
    db_session.remove()
