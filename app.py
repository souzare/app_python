from flask import Flask, render_template, request, url_for, flash, redirect
from werkzeug.exceptions import abort
import sqlite3
import os
from prometheus_client import Counter, Histogram, Gauge
from prometheus_flask_exporter import PrometheusMetrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry import metrics
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.sqlite3 import SQLite3Instrumentor
from opentelemetry.sdk.resources import Resource

# Configuração do OpenTelemetry para métricas
metric_exporter = OTLPMetricExporter(endpoint="http://otel-collector:4317", insecure=True)
metric_reader = PeriodicExportingMetricReader(metric_exporter)

meter_provider = MeterProvider(metric_readers=[metric_reader], resource=Resource.create({"service.name": "flask-blog-app"}))
metrics.set_meter_provider(meter_provider)
meter = metrics.get_meter("flask-blog-app")

# Métricas OpenTelemetry
REQUESTS_COUNT = meter.create_counter("http_requests_total", "Total number of requests")
LATENCY = meter.create_histogram("http_request_duration_seconds", "Request latency in seconds")
ERRORS = meter.create_counter("http_request_errors_total", "Total number of request errors")
POSTS_COUNT = meter.create_gauge("posts_count", "Current number of posts")

# Inicialização da aplicação Flask
app = Flask(__name__)
app.config['SECRET_KEY'] = '1234'

# Instrumentação OpenTelemetry
FlaskInstrumentor().instrument_app(app)
SQLite3Instrumentor().instrument()

# Instrumentação Prometheus
metrics_prom = PrometheusMetrics(app)

# Função para conectar ao banco de dados SQLite
def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

# Função para buscar um post específico
def get_post(post_id):
    conn = get_db_connection()
    post = conn.execute('SELECT * FROM posts WHERE id = ?', (post_id,)).fetchone()
    conn.close()
    if post is None:
        abort(404)
    return post

@app.route('/')
def index():
    conn = get_db_connection()
    posts = conn.execute('SELECT * FROM posts').fetchall()
    conn.close()

    REQUESTS_COUNT.add(1)
    POSTS_COUNT.set(len(posts))

    with LATENCY.record(amount=1):
        return render_template('index.html', posts=posts)

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
            conn.execute('INSERT INTO posts (title, content) VALUES (?, ?)', (title, content))
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
            conn.execute('UPDATE posts SET title = ?, content = ? WHERE id = ?', (title, content, id))
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
    flash(f'"{post["title"]}" was successfully deleted!')
    return redirect(url_for('index'))

@app.route('/error')
def error():
    ERRORS.add(1, {"error_type": "500"})
    return "Internal Server Error", 500

@app.route('/notfound')
def not_found():
    ERRORS.add(1, {"error_type": "404"})
    return "Not Found", 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
