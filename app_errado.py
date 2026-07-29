from flask import Flask, render_template, request, url_for, flash, redirect
from werkzeug.exceptions import abort
import sqlite3
import time

from opentelemetry.metrics import Observation

from telemetry import setup_telemetry

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def get_post(post_id):
    conn = get_db_connection()
    post = conn.execute('SELECT * FROM posts WHERE id = ?',
                        (post_id,)).fetchone()
    conn.close()
    if post is None:
        abort(404)
    return post

app = Flask(__name__)
app.config['SECRET_KEY'] = '1234'
meter = setup_telemetry(app, service_name="app_python")

REQUEST_COUNTER = meter.create_counter(
    "http_requests_total", description="Total number of requests made")
LATENCY_HISTOGRAM = meter.create_histogram(
    "http_request_duration_seconds", unit="s", description="Request latency in seconds")
ERROR_COUNTER = meter.create_counter(
    "http_request_errors_total", description="Total number of request errors")

def _posts_count_callback(options):
    conn = get_db_connection()
    count = conn.execute('SELECT COUNT(*) FROM posts').fetchone()[0]
    conn.close()
    yield Observation(count)

meter.create_observable_gauge(
    "posts_count",
    callbacks=[_posts_count_callback],
    description="Current number of posts",
)

@app.before_request
def before_request():
    request.start_time = time.time()
    REQUEST_COUNTER.add(1)

@app.after_request
def after_request(response):
    LATENCY_HISTOGRAM.record(time.time() - request.start_time)
    return response

@app.route('/')
def index():
    # Redireciona a home da aplicacao para o endpoint de erro (demo de SLO)
    ERROR_COUNTER.add(1, {"error_type": "500"})
    return "Internal Server Error", 500

@app.route('/<int:post_id>')
def post(post_id):
    post = get_post(post_id)
    return render_template('post.html', post=post)

@app.route('/create', methods=('GET', 'POST'))
def create():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']

        if not title:
            flash('Title is required!')
        else:
            conn = get_db_connection()
            conn.execute('INSERT INTO posts (title, content) VALUES (?, ?)',
                         (title, content))
            conn.commit()
            conn.close()
            return redirect(url_for('index'))
    return render_template('create.html')

@app.route('/<int:id>/edit', methods=('GET', 'POST'))
def edit(id):
    post = get_post(id)

    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']

        if not title:
            flash('Title is required!')
        else:
            conn = get_db_connection()
            conn.execute('UPDATE posts SET title = ?, content = ?'
                         ' WHERE id = ?',
                         (title, content, id))
            conn.commit()
            conn.close()
            return redirect(url_for('index'))

    return render_template('edit.html', post=post)

@app.route('/<int:id>/delete', methods=('POST',))
def delete(id):
    post = get_post(id)
    conn = get_db_connection()
    conn.execute('DELETE FROM posts WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    flash('"{}" was successfully deleted!'.format(post['title']))
    return redirect(url_for('index'))

@app.route('/error')
def error():
    # Simulate a 500 Internal Server Error
    ERROR_COUNTER.add(1, {"error_type": "500"})
    return "Internal Server Error", 500

@app.route('/notfound')
def not_found():
    # Simulate a 404 Not Found Error
    ERROR_COUNTER.add(1, {"error_type": "404"})
    return "Not Found", 404

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
