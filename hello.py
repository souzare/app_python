from flask import Flask, render_template
import sqlite3
import os
from prometheus_client import Counter, Histogram
from prometheus_flask_exporter import PrometheusMetrics

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

app = Flask(__name__)
metrics = PrometheusMetrics(app)

REQUEST = Counter("http_requests_total", "Total number of requests made")
LATENCY = Histogram("http_request_duration_seconds", "Request latency in seconds")
ERRORS = Counter("http_request_errors_total", "Total number of request errors", ["error_type"])

@app.route('/')
def index():
    conn = get_db_connection()
    posts = conn.execute('SELECT * FROM posts').fetchall()
    conn.close()
    REQUEST.inc()
    return render_template('index.html', posts=posts)

@app.route('/error')
def error():
    # Simulate a 500 Internal Server Error
    ERRORS.labels(error_type="500").inc()
    return "Internal Server Error", 500

@app.route('/notfound')
def not_found():
    # Simulate a 404 Not Found Error
    ERRORS.labels(error_type="404").inc()
    return "Not Found", 404

app.run(host='0.0.0.0', port=5000)
