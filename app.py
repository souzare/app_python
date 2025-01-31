from flask import Flask, render_template, request, url_for, flash, redirect
from werkzeug.exceptions import abort
import sqlite3
from prometheus_client import Counter, Histogram, Gauge
from prometheus_flask_exporter import PrometheusMetrics
from opentelemetry import trace, metrics
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.sqlite3 import SQLite3Instrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter

# Configurar OpenTelemetry
resource = Resource.create({"service.name": "flask-blog-app"})

# Tracing
trace.set_tracer_provider(TracerProvider(resource=resource))
tracer = trace.get_tracer(__name__)
span_processor = BatchSpanProcessor(OTLPSpanExporter(endpoint="http://otel-collector:4317"))
trace.get_tracer_provider().add_span_processor(span_processor)

# Métricas
metrics.set_meter_provider(MeterProvider(resource=resource))
meter = metrics.get_meter(__name__)
metric_exporter = OTLPMetricExporter(endpoint="http://otel-collector:4317")
metrics.get_meter_provider().start_pipeline(meter, metric_exporter, 5)

# Instrumentação automática
FlaskInstrumentor().instrument_app(app)
SQLite3Instrumentor().instrument()

app = Flask(__name__)
app.config['SECRET_KEY'] = '1234'
metrics = PrometheusMetrics(app)

REQUEST = Counter("http_requests_total", "Total number of requests made")
LATENCY = Histogram("http_request_duration_seconds", "Request latency in seconds")
ERRORS = Counter("http_request_errors_total", "Total number of request errors", ["error_type"])

# Métrica Gauge para monitorar o número de posts
POSTS_COUNT = Gauge("posts_count", "Current number of posts")

@app.route('/')
def index():
    with tracer.start_as_current_span("index"):
        conn = get_db_connection()
        posts = conn.execute('SELECT * FROM posts').fetchall()
        conn.close()
        REQUEST.inc()

        # Definir o valor da métrica de Gauge
        POSTS_COUNT.set(len(posts))
        
        # Simulating latency measurement
        with LATENCY.time():
            return render_template('index.html', posts=posts)

@app.route('/<int:post_id>')
def post(post_id):
    with tracer.start_as_current_span("view_post"):
        post = get_post(post_id)
        return render_template('post.html', post=post)

@app.route('/create', methods=('GET', 'POST'))
def create():
    with tracer.start_as_current_span("create_post"):
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

@app.route('/error')
def error():
    with tracer.start_as_current_span("error_simulation"):
        ERRORS.labels(error_type="500").inc()
        return "Internal Server Error", 500

app.run(host='0.0.0.0', port=5000)
