
from hummaps.database import db_session
from hummaps.models import Surveyor
# from hummaps.models_paths import Surveyor


def xhr_request(req):

    response = None
    if req == 'surveyors':
        q = db_session.query(Surveyor).order_by(Surveyor.lastname, Surveyor.firstname)
        response = tuple(s.name for s in q.all())

    return response


if __name__ == '__main__':

    from flask import Flask

    app = Flask(__name__)
    with app.app_context():

        resp = xhr_request('surveyors')
        print('length: %d' % (len(resp)))
        print(resp)
