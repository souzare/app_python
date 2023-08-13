from flask import Flask, render_template
import sqlite3
import os
from prometheus_client import Counter, generate_latest

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn


app = Flask(__name__)

# Definindo a métrica Counter para contagem de solicitações HTTP
http_requests_total = Counter(
    'http_requests_total',
    'Total number of HTTP requests',
    ['endpoint', 'http_status']
)

@app.route('/')
def index():
    conn = get_db_connection()
    posts = conn.execute('SELECT * FROM posts').fetchall()
    conn.close()
    return render_template('index.html', posts=posts)

@app.route('/metrics')
def metrics():
    return Response(generate_latest(), mimetype='text/plain')

app.run(host='0.0.0.0', port=5000)

# if __name__ == "__main__":
#     port = int(os.environ.get('PORT', 5000))
#     app.run(debug=True, host='0.0.0.0', port=port)