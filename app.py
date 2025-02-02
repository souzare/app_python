# filepath: /C:/GitRepo/app_python/app.py
from flask import Flask, render_template, request, url_for, flash, redirect
from werkzeug.exceptions import abort
import sqlite3
import os
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from prometheus_flask_exporter import PrometheusMetrics
from jaeger_client import Config
import logging
import time

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
metrics = PrometheusMetrics(app)

REQUEST = Counter("http_requests_total", "Total number of requests made")
LATENCY = Histogram("http_request_duration_seconds", "Request latency in seconds")
ERRORS = Counter("http_request_errors_total", "Total number of request errors", ["error_type"])

# Métrica Gauge para monitorar o número de posts
POSTS_COUNT = Gauge("posts_count", "Current number of posts")

# Configurar o Jaeger Tracer
def init_tracer(service):
    logging.getLogger('').handlers = []
    logging.basicConfig(format='%(message)s', level=logging.DEBUG)

    config = Config(
        config={
            'sampler': {'type': 'const', 'param': 1},
            'logging': True,
            'local_agent': {'reporting_host': 'jaeger', 'reporting_port': '6831'},
        },
        service_name=service,
        validate=True,
    )
    return config.initialize_tracer()

tracer = init_tracer('app_python')

@app.before_request
def before_request():
    request.start_time = time.time()
    REQUEST.inc()
    span = tracer.start_span(request.path)
    request.span = span

@app.after_request
def after_request(response):
    request_latency = time.time() - request.start_time
    LATENCY.observe(request_latency)
    request.span.finish()
    return response

@app.route('/')
def index():
    conn = get_db_connection()
    posts = conn.execute('SELECT * FROM posts').fetchall()
    conn.close()
    POSTS_COUNT.set(len(posts))
    return render_template('index.html', posts=posts)

@app.route('/post/<int:post_id>')
def post(post_id):
    post = get_post(post_id)
    return render_template('post.html', post=post)

@app.route('/metrics')
def metrics():
    return generate_latest()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)