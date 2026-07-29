import os

from opentelemetry import metrics
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import SERVICE_NAME, Resource

_meter = None


def setup_telemetry(app, service_name=None):
    """Wire a Flask app to push metrics via OTLP to an OTel Collector.

    Reads the collector address from OTEL_EXPORTER_OTLP_ENDPOINT (falls back
    to the SDK default of http://localhost:4317) so the same code works
    unchanged across docker-compose (service DNS) and ECS host networking
    (localhost).
    """
    global _meter

    name = service_name or os.environ.get("OTEL_SERVICE_NAME", "app_python")
    resource = Resource.create({SERVICE_NAME: name})

    meter_provider = MeterProvider(
        resource=resource,
        metric_readers=[PeriodicExportingMetricReader(OTLPMetricExporter())],
    )
    metrics.set_meter_provider(meter_provider)

    # Auto-instruments HTTP server metrics (request duration/count per route)
    # on top of the custom business metrics defined in the app itself.
    FlaskInstrumentor().instrument_app(app)

    _meter = metrics.get_meter(name)
    return _meter


def get_meter():
    if _meter is None:
        raise RuntimeError("setup_telemetry() must run before get_meter()")
    return _meter
