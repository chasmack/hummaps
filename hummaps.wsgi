
# Setup the virtual environment

# activate_this = '/home/ubuntu/www/hummaps/venv/bin/activate_this.py'
# with open(activate_this) as file_:
#     exec(file_.read(), dict(__file__=activate_this))

import sys
sys.path.insert(0, '/var/www/html/hummaps')

#from test import app as application
from hummaps import app as application

