# filepath: /c:/GitRepo/app_python/app.py
from flask import Flask, render_template, request, url_for, flash, redirect
from werkzeug.exceptions import abort
import sqlite3
import os
from prometheus_client import Counter, Histogram, Gauge
from prometheus_flask_exporter import PrometheusMetrics
from opentelemetry import trace, metrics
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.wsgi import OpenTelemetryMiddleware
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
prometheus_metrics = PrometheusMetrics(app)
FlaskInstrumentor().instrument_app(app)
app.wsgi_app = OpenTelemetryMiddleware(app.wsgi_app)

REQUEST = Counter("http_requests_total", "Total number of requests made")
LATENCY = Histogram("http_request_duration_seconds", "Request latency in seconds")
ERRORS = Counter("http_request_errors_total", "Total number of request errors", ["error_type"])

# Métrica Gauge para monitorar o número de posts
POSTS_COUNT = Gauge("posts_count", "Current number of posts")

# Configure the tracer provider and exporter
resource = Resource(attributes={
    "service.name": "app_python"
})
trace.set_tracer_provider(TracerProvider(resource=resource))
tracer_provider = trace.get_tracer_provider()
otlp_trace_exporter = OTLPSpanExporter(endpoint="http://otel-collector:4318/v1/traces")
span_processor = BatchSpanProcessor(otlp_trace_exporter)
tracer_provider.add_span_processor(span_processor)

# Configure the meter provider and exporter
otlp_metric_exporter = OTLPMetricExporter(endpoint="http://otel-collector:4318/v1/metrics")
metric_reader = PeriodicExportingMetricReader(otlp_metric_exporter)
meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
metrics.set_meter_provider(meter_provider)

@app.before_request
def before_request():
    request.start_time = time.time()
    REQUEST.inc()

@app.after_request
def after_request(response):
    request_latency = time.time() - request.start_time
    LATENCY.observe(request_latency)
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

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)