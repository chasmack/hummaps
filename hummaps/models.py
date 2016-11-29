from sqlalchemy.orm import relationship
from sqlalchemy import Table, Column, Integer, String, Date, ForeignKey
from sqlalchemy.ext.hybrid import hybrid_property, hybrid_method

from hummaps.database import Base


class MapImage(Base):
    __tablename__ = 'map_image'

    id = Column(Integer, primary_key=True)
    map_id = Column(Integer, ForeignKey('map.id'))
    page = Column(Integer)
    imagefile = Column(String)

    map = relationship('Map', back_populates='mapimages')

    def __repr__(self):
        return '<MapImage(id=%d, map=%d, imagefile="%s")>' % (self.id, self.map_id, self.imagefile)


class CCImage(Base):
    __tablename__ = 'cc_image'

    id = Column(Integer, primary_key=True)
    cc_id = Column(Integer, ForeignKey('cc.id'))
    page = Column(Integer)
    imagefile = Column(String)

    cc = relationship('CC', back_populates='ccimages')

    def __repr__(self):
        return '<CCImage(id=%d, cc=%d, imagefile="%s")>' % (self.id, self.cc_id, self.imagefile)


class CC(Base):
    __tablename__ = 'cc'

    id = Column(Integer, primary_key=True)
    map_id = Column(Integer, ForeignKey('map.id'))
    doc_number = Column(String)
    npages = Column(Integer)

    map = relationship('Map', back_populates='certs')
    ccimages = relationship('CCImage', order_by=CCImage.page, back_populates='cc')

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
    subsec = Column(Integer)
    source_id = Column(Integer, ForeignKey('source.id'))

    map = relationship('Map', back_populates='trs')
    source = relationship('Source', back_populates='trs')

    def __repr__(self):
        return '<TRS(id=%d)>' % (self.id)


class MapType(Base):
    __tablename__ = 'maptype'

    id = Column(Integer, primary_key=True)
    maptype = Column(String)
    abbrev = Column(String)

    map = relationship('Map', back_populates='maptype')

    def __repr__(self):
        return '<MapType(id=%d, maptype="%s", abbrev="%s")>' % (self.id, self.maptype, self.abbrev)


# Association table for the many to many relationship between Map <-> Surveyor
signed_by = Table('signed_by', Base.metadata,
    Column('map_id', Integer, ForeignKey('map.id'), primary_key=True),
    Column('surveyor_id', Integer, ForeignKey('surveyor.id'), primary_key=True)
)


class Surveyor(Base):
    __tablename__ = 'surveyor'

    id = Column(Integer, primary_key=True)
    fullname = Column(String)
    firstname = Column(String)
    secondname = Column(String)
    thirdname = Column(String)
    lastname = Column(String)
    suffix = Column(String)
    pls = Column(String)
    rce = Column(String)

    # many to many Map <-> Surveyor
    map = relationship('Map', secondary=signed_by, back_populates='surveyor')

    @hybrid_property
    def name(self):
        name = [self.firstname]
        if self.secondname:
            name.append(self.secondname[0] + '.')
        if self.thirdname:
            name.append(self.thirdname[0] + '.')
        name.append(self.lastname)
        name = ' '.join(name).title()
        if self.suffix:
            name += ' ' + self.suffix
        return name

    def __repr__(self):
        return '<Surveyor(id=%d, fullname="%s")>' % (self.id, self.fullname)


class Map(Base):
    __tablename__ = 'map'

    id = Column(Integer, primary_key=True)
    maptype_id = Column(Integer, ForeignKey('maptype.id'))
    book = Column(Integer)
    page = Column(Integer)
    npages = Column(Integer)
    recdate = Column(Date)
    client = Column(String)
    description = Column(String)
    note = Column(String)

    trs = relationship('TRS', back_populates='map')
    mapimages = relationship('MapImage', order_by=MapImage.page, back_populates='map')
    maptype = relationship('MapType', back_populates='map')
    certs = relationship('CC', back_populates='map')

    # many to many Map <-> Surveyor
    surveyor = relationship('Surveyor', secondary=signed_by, back_populates='map')

    @hybrid_property
    def heading(self):
        h = '%d of %ss' % (self.book, self.maptype.maptype)
        if self.npages > 1:
            h += ' %d-%d' % (self.page, self.page + self.npages - 1)
            # h += ' Pages %d-%d' % (self.mapPage, self.mapPage + self.npages - 1)
        else:
            h += ' %d' % (self.page)
            # h += ' Page %d' % (self.mapPage)
        return h

    @hybrid_property
    def line1(self):
        surveyors = []
        for s in self.surveyor:
            lics = []
            if s.pls:
                lics.append('LS' + s.pls)
            if s.rce:
                lics.append('RCE' + s.rce)
            if lics:
                lics = ' (' + ', '.join(lics) + ')'
            else:
                lics = ''
            surveyors.append(s.name + lics)
        if surveyors:
            surveyors = ', '.join(surveyors)
        else:
            surveyors = '(UNKNOWN)'

        recdate =self.recdate.strftime(' %m/ %d/%Y').replace(' 0', '').replace(' ', '')

        return 'Recorded %s by %s' % (recdate, surveyors)

    @hybrid_property
    def line2(self):
        return 'For ' + self.client if self.client else None

    @hybrid_property
    def line3(self):
        return self.description

    @hybrid_property
    def bookpage(self):
        return '%03d%s%03d' % (self.book, self.maptype.abbrev.upper(), self.page)

    @hybrid_method
    def url(self, page=1):
        nimages = len(self.mapimages)
        if nimages == 0:
            return None
        img = self.mapimages[nimages - 1] if page > nimages else self.mapimages[page - 1]

        return img.imagefile

    def __repr__(self):
        return '<Map(id=%d, map="%s")>' % (self.id, self.bookpage)



if __name__ == '__main__':

    pass