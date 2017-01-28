from flask import request
from flask import render_template, flash

from hummaps import app
from hummaps.search import do_search, ParseError

from hummaps.gpx import gpx_read, gpx_out
from hummaps.gpx import dxf_read, dxf_out
from hummaps.gpx import pnts_read, pnts_out


@app.route('/', methods=['GET'])
def index():

    q = request.args.get('q', '')
    if q == '':
        return render_template('index.html', query='', results=[])

    results = []
    try:
        results = do_search(q)
    except ParseError as e:
        term = ' (%s)' % e.term if e.term else ''
        flash('Search error%s: <strong>%s</strong>' % (term, e.err), 'error')
    except Exception as e:
        flash('Search error: <strong>%s</strong>' % str(e), 'error')

    total = len(results)
    if total > 200:
        results = results[0:200]

    return render_template('index.html', query=q, results=results, total=total)


@app.route('/hummaps-dev', methods=['GET'])
def dev():

    q = request.args.get('q', '')
    if q == '':
        return render_template('hummaps-dev.html', query='', results=[])

    results = []
    try:
        results = do_search(q)
    except ParseError as e:
        term = ' (%s)' % e.term if e.term else ''
        flash('Search error%s: <strong>%s</strong>' % (term, e.err), 'error')
    except Exception as e:
        flash('Search error: <strong>%s</strong>' % str(e), 'error')

    total = len(results)
    if total > 250:
        results = results[0:250]

    return render_template('hummaps-dev.html', query=q, results=results, total=total)


@app.route('/gpx', methods=['GET', 'POST'])
def gpx():
    if request.method == 'POST':
        datatype = request.form['datatype']
        srid = int(request.form['srid'])
        files = request.files.getlist('file')
        headers = 'type: ' + datatype + ', srid: ' + str(srid) + ', files: ' + ', '.join([f.filename for f in files]) + '\n'
        geom = []
        for f in request.files.getlist('file'):
            filename = f.filename
            ext = filename.lower().rsplit('.', 1)[-1]
            if ext == 'txt':
                geom += pnts_read(f.stream, srid)
            elif ext == 'dxf':
                geom += dxf_read(f.stream, srid)
            elif ext == 'gpx':
                geom += gpx_read(f.stream)
        data = headers
        if datatype == 'pnts':
            data += pnts_out(geom, srid)
        elif datatype == 'dxf':
            data += dxf_out(geom, srid)
        elif datatype == 'gpx':
            data += gpx_out(geom)
        else:
            data += 'Unknown data type: ' + datatype
        return data

    return render_template('gpx.html')


#
# HTTP error handlers
#

@app.errorhandler(403)
def forbidden(e):
    return render_template('403.html'), 403

@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500
