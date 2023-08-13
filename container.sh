#!/bin/bash
docker rm -f python
docker image build -t flask_docker .
docker run --name "python" -p 5000:5000 -d flask_docker