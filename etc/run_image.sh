#!/bin/bash

docker run -p 8501:8501 -p 5000:5000 \
  -e HARDWARE_MOCK=true \
  -e DEBUG=true \
  -e API_SERVER=5000 \
  -e PORT=8501 \
  -e ENV=development \
  pyrigol