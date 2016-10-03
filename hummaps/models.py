from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, String, Date, ForeignKey

from hummaps.database import Base


class MapImage(Base):
    __tablename__ = 'map_image'

    id = Column(Integer, primary_key=True)
    map_id = Column(Integer, ForeignKey('map.id'))
    page = Column(Integer)
    imagefile = Column(String)

    map = relationship('Map', back_populates='mapimage')

    def __repr__(self):
        return '<MapImage(id=%d, map=%d, imagefile="%s")>' % (self.id, self.map_id, self.imagefile)


class CCImage(Base):
    __tablename__ = 'cc_image'

    id = Column(Integer, primary_key=True)
    cc_id = Column(Integer, ForeignKey('cc.id'))
    page = Column(Integer)
    imagefile = Column(String)

    cc = relationship('CC', back_populates='ccimage')

    def __repr__(self):
        return '<CCImage(id=%d, cc=%d, imagefile="%s")>' % (self.id, self.cc_id, self.imagefile)


class CC(Base):
    __tablename__ = 'cc'

    id = Column(Integer, primary_key=True)
    map_id = Column(Integer, ForeignKey('map.id'))
    doc_number = Column(String)
    npages = Column(Integer)

    map = relationship('Map', back_populates='cc')
    ccimage = relationship('CCImage', order_by=CCImage.page, back_populates='cc')

    def __repr__(self):
        return '<CC(id=%d, doc="%s")>' % (self.id, self.doc_number)


class Source(Base):
    __tablename__ = 'source'

    id = Column(Integer, primary_key=True)
    description = Column(String)
    quality = Column(Integer)

    trs = relationship('TRS', back_populates='source')

    def __repr__(self):
        return '<Source(id=%d, desc="%s", quality=%d)>' % (self.id, self.description, self.quality)


class TRS(Base):
    __tablename__ = 'trs'

    id = Column(Integer, primary_key=True)
    map_id = Column(Integer, ForeignKey('map.id'))
    tshp = Column(Integer)
    rng = Column(Integer)
    sec = Column(Integer)
    qqsec = Column(Integer)
    source_id = Column(Integer, ForeignKey('source.id'))

    map = relationship('Map', back_populates='trs')
    source = relationship('Source', back_populates='trs')

    def __repr__(self):
        return '<TRS(id=%d)>' % (self.id)


class Map(Base):
    __tablename__ = 'map'

    id = Column(Integer, primary_key=True)
    maptype_id = Column(Integer, ForeignKey('maptype.id'))
    book = Column(Integer)
    page = Column(Integer)
    npages = Column(Integer)
    recdate = Column(Date)
    surveyor_id = Column(Integer, ForeignKey('surveyor.id'))
    client = Column(String)
    description = Column(String)
    note = Column(String)

    trs = relationship('TRS', back_populates='map')
    mapimage = relationship('MapImage', order_by=MapImage.page, back_populates='map')
    maptype = relationship('MapType', back_populates='map')
    surveyor = relationship('Surveyor', back_populates='map')
    cc = relationship('CC', back_populates='map')

    def bookpage(self):
        return '%03d%s%03d' % (self.book, self.maptype.abbrev.upper(), self.page)

    def __repr__(self):
        return '<Map(id=%d, map="%s")>' % (self.id, self.bookpage())


class MapType(Base):
    __tablename__ = 'maptype'

    id = Column(Integer, primary_key=True)
    maptype = Column(String)
    abbrev = Column(String)

    map = relationship('Map', back_populates='maptype')

    def __repr__(self):
        return '<MapType(id=%d, maptype="%s", abbrev="%s")>' % (self.id, self.maptype, self.abbrev)


class Surveyor(Base):
    __tablename__ = 'surveyor'

    id = Column(Integer, primary_key=True)
    lastname = Column(String)
    fullname = Column(String)
    pls = Column(Integer)
    rce = Column(Integer)

    map = relationship('Map', back_populates='surveyor')

    def __repr__(self):
        return '<Surveyor(id=%d, fullname="%s")>' % (self.id, self.fullname)




if __name__ == '__main__':
    pass