from flask import request
from flask import render_template, flash

from hummaps import app
from hummaps.search import do_search, ParseError


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
    if total > 100:
        results = results[0:100]

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
    if total > 100:
        results = results[0:100]

    return render_template('hummaps-dev.html', query=q, results=results, total=total)


@app.route('/gpx', methods=['GET', 'POST'])
def gpx():

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
