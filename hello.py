from flask import Flask, render_template
import sqlite3
import os
from prometheus_client import Counter #Prometheus lib
from prometheus_flask_exporter import PrometheusMetrics

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

REQUESTS = Counter("requests_total", "Total number of requests made") #metricas do prmetheus
app = Flask(__name__)
metrics = PrometheusMetrics(app)
@app.route('/')
def index():
    conn = get_db_connection()
    posts = conn.execute('SELECT * FROM posts').fetchall()
    conn.close()
    REQUESTS.inc() #metricas do prmetheus
    return render_template('index.html', posts=posts)

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)