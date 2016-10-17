from flask import redirect, url_for, make_response
from flask import abort, render_template, flash
from flask.ext.login import login_user, logout_user, current_user, login_required

from hummaps import app
from hummaps.database import db_session
from hummaps.forms import SearchForm
from hummaps.search import do_search, ParseError


@app.route('/')
def search():
    form = SearchForm()
    return render_template('search.html', form=form)


@app.route('/results', methods=['GET', 'POST'])
def show_results():
    form = SearchForm()
    results = []
    if form.validate_on_submit():
        try:
            results = do_search(form.description.data)
        except ParseError as e:
            term = ' (%s)' % e.term if e.term else ''
            flash('Search format error%s: <strong>%s</strong>' % (term, e.err), 'error')
        except Exception as e:
            flash('<strong>Search Error:</strong> %s' % str(e), 'error')

    count = len(results)
    if count > 200:
        results = results[0:200]

    return render_template('results.html', count=count, results=results)


@app.route('/show', methods=['GET'])
def show_map():

    return render_template('show_map.html')


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
