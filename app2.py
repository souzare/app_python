from flask import Flask, render_template, request, url_for, flash, redirect
from werkzeug.exceptions import abort
import sqlite3
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = '1234'
#monitoramento Elastic
from elasticapm.contrib.flask import ElasticAPM
app.config['ELASTIC_APM'] = {
  'SERVICE_NAME': 'Python',

  'SECRET_TOKEN': 'ePqEgkp1QESVHzKNwK',

  'SERVER_URL': 'https://83bdca7098464ab69ad360be80950c3d.apm.us-east-2.aws.elastic-cloud.com:443',

  'ENVIRONMENT': 'Dev',
}
apm = ElasticAPM(app)

@app.route('/')
def hello():
    return 'Hello, World!'

@app.route('/error')
def error():
    # Simulate a 500 Internal Server Error
    return "Internal Server Error", 500

@app.route('/notfound')
def not_found():
    # Simulate a 404 Not Found Error
    return "Not Found", 404

app.run(host='0.0.0.0', port=5000)
