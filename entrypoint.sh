#!/bin/bash

# Start with an empty args string
ARGS=""

# Check for each environment variable and set the corresponding argument
if [ "$HARDWARE_MOCK" = "true" ]; then
    ARGS="$ARGS --hardware-mock"
fi

if [ "$DEBUG" = "true" ]; then
    ARGS="$ARGS --debug"
fi

if [ ! -z "$API_SERVER" ]; then
    ARGS="$ARGS --api-server $API_SERVER"
fi

if [ ! -z "$PORT" ]; then
    ARGS="$ARGS --port $PORT"
else
    ARGS="$ARGS --port 8501"
fi

if [ ! -z "$ENV" ]; then
    ARGS="$ARGS --env $ENV"
else
    ARGS="$ARGS --env development"
fi

# Execute the main application with the composed arguments
exec pipenv run bash $CONFIG/environment.sh
exec pipenv run python main.py $ARGS
