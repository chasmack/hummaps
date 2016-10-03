from sqlalchemy import func

from hummaps.database import db_session
from hummaps.models import Map, MapImage, TRS, Source, MapType, Surveyor, CC, CCImage


def do_search(desc):

    # stmt = db_session.query(CC.map_id, func.count('*').label('cc_count'))
    # stmt = stmt.group_by(CC.map_id).subquery()

    # query = db_session.query(Map, func.coalesce(stmt.c.cc_count, 0).label('cc_count'))
    # query = query.outerjoin(stmt, Map.id == stmt.c.map_id)

    query = db_session.query(Map).join(TRS).join(MapType)
    query = query.filter(TRS.tshp == 6, TRS.rng == 0, TRS.sec == 32)
    query = query.filter(TRS.qqsec.op('&')(1) != 0)
    # query = query.filter(Map.description.op('~')('.*NW/4 S32'))
    query = query.order_by(MapType.abbrev, Map.recdate.desc())

    maps = query.all()

    return maps

if __name__ == '__main__':

    results = do_search('nw/4 s32 t7n r1s')
    for map in results:

        mapimages = ', '.join([mapimage.imagefile for mapimage in map.mapimage])
        if mapimages == '':
            mapimages = 'None'

        certs = []
        for cc in map.cc:
            imagefiles = ', '.join([ccimage.imagefile for ccimage in cc.ccimage])
            if imagefiles == '':
                imagefiles = 'None'
            certs.append('CC=%s (%s)' % (cc.doc_number, imagefiles))
        certs = ', '.join(certs)

        print('%06d: %s (%s) %s' % (map.id, map.bookpage(), mapimages, certs))

    print('%d maps found.' % (len(results)))


