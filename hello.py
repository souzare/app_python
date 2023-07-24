from flask import Flask, render_template
from prometheus_client import Counter #Prometheus lib
from prometheus_flask_exporter import PrometheusMetrics

app = Flask(__name__)
metrics = PrometheusMetrics(app)
@app.route('/')
def index():
    return render_template('index.html')