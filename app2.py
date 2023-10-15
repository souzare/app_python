from flask import Flask
from elasticapm.contrib.flask import ElasticAPM

app = Flask(__name__)

#monitoramento Elastic
app.config['ELASTIC_APM'] = {
  'SERVICE_NAME': 'Python',

  'SECRET_TOKEN': 'ePqEgkp1QESVHzKNwK',

  'SERVER_URL': 'https://83bdca7098464ab69ad360be80950c3d.apm.us-east-2.aws.elastic-cloud.com:443',

  'ENVIRONMENT': 'Dev',
}
apm = ElasticAPM(app)

@app.route('/')
def index():
    return 'Hello, World!'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
