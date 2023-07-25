from flask import Flask, render_template
import sqlite3
from prometheus_client import Counter #Prometheus lib
from prometheus_flask_exporter import PrometheusMetrics

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

REQUESTS = Counter("requests_total", "Total number of requests made")
app = Flask(__name__)
metrics = PrometheusMetrics(app)
@app.route('/')
def index():
    conn = get_db_connection()
    posts = conn.execute('SELECT * FROM posts').fetchall()
    conn.close()
    REQUESTS.inc()
    return render_template('index.html')