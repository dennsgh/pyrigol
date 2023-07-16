# Use an official Python runtime as a parent image
FROM python:3.8

# Set environment variables
ENV NAME=pyrigol \
    WORKINGDIR=/pyrigol \
    CONFIG=/pyrigol/etc \
    DATA=/pyrigol/data \
    PYTHONPATH="/app/src:/app/frontend/src"

# Set the working directory in the container
WORKDIR ${WORKINGDIR}

# Install any needed packages specified in Pipfile
COPY Pipfile Pipfile.lock ./
RUN pip install pipenv && pipenv install --system --deploy

# Copy the rest of the working directory contents into the container at /app
COPY . ./

# Make ports 8501 available to the world outside this container
EXPOSE 8501

# Run app.py when the container launches
CMD ["python", "main.py"]
