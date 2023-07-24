from flask import Flask, render_template
from prometheus_client import Counter #Prometheus lib

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

#Prometheus monitoring
c = Counter('my_failures', 'Description of counter')
c.inc()     # Increment by 1
c.inc(1.6)  # Increment by given value