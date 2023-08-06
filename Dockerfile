# Use an official Python runtime as a parent image
FROM python:3.8

# Set environment variables
ENV NAME=pyrigol \
    WORKINGDIR=/pyrigol \
    CONFIG=/pyrigol/etc \
    DATA=/pyrigol/data \
    PYTHONPATH="/pyrigol/src:/pyrigol/frontend/src"

# Set the working directory in the container
WORKDIR /pyrigol

# Install any needed packages specified in Pipfile
#COPY Pipfile Pipfile.lock ./

# Copy the rest of the working directory contents into the container at /app
COPY . /pyrigol
RUN cd /pyrigol
RUN pip install pipenv && pipenv install --deploy --ignore-pipfile

# Make ports 8501 available to the world outside this container
EXPOSE 8501
EXPOSE 5000

# Define environment variable for ensuring that Python outputs everything that's printed inside
# the application rather than buffering it.
ENV PYTHONUNBUFFERED 1

# Run the app command when the container launches
ENTRYPOINT ["/pyrigol/entrypoint.sh"]
