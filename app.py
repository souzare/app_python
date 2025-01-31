# filepath: /C:/GitRepo/app_python/app.py
from flask import Flask
from opentelemetry import trace, metrics
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.wsgi import OpenTelemetryMiddleware

# Configure the tracer provider and exporter
resource = Resource(attributes={
    "service.name": "app_python"
})
trace.set_tracer_provider(TracerProvider(resource=resource))
tracer_provider = trace.get_tracer_provider()
otlp_trace_exporter = OTLPSpanExporter(endpoint="http://otel-collector:4317", insecure=True)
span_processor = BatchSpanProcessor(otlp_trace_exporter)
tracer_provider.add_span_processor(span_processor)

# Configure the meter provider and exporter
metrics.set_meter_provider(MeterProvider(resource=resource))
meter_provider = metrics.get_meter_provider()
otlp_metric_exporter = OTLPMetricExporter(endpoint="http://otel-collector:4317", insecure=True)
metric_reader = PeriodicExportingMetricReader(otlp_metric_exporter)
meter_provider.start_pipeline(metric_reader, 60)

app = Flask(__name__)
FlaskInstrumentor().instrument_app(app)
app.wsgi_app = OpenTelemetryMiddleware(app.wsgi_app)

# Example of creating a counter metric
meter = metrics.get_meter(__name__)
request_counter = meter.create_counter(
    name="request_counter",
    description="Counts the number of requests",
    unit="1",
)

@app.before_request
def before_request():
    request_counter.add(1, {"endpoint": request.endpoint})

# ...existing code...

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)