#!/bin/bash
docker rm -f python
docker image build -t flask_docker .
docker run --name "python" -p 5000:5000 --network=app_node_default -d flask_docker