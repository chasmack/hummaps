from hummaps.database import db_session
from hummaps.models import Map, MapImage, TRS, Source, MapType, Surveyor, CC, CCImage


def xhr_request(req):

    response = None
    if req == 'surveyors':
        q = db_session.query(Surveyor).order_by(Surveyor.lastname, Surveyor.firstname)
        response = tuple(s.name for s in q.all())

    return response


if __name__ == '__main__':

    pass