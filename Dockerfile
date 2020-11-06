# Use an official lightweight Python image.
# https://hub.docker.com/_/python
FROM python:3.8-slim

ENV APP_HOME /waste_d
WORKDIR $APP_HOME

# Install dependencies.
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy local code to the container image.
COPY . .

# Service must listen to $PORT environment variable.
# This default value facilitates local development.
ENV PORT 8000

# Setting this ensures print statements and log messages
# promptly appear in Cloud Logging.
ENV PYTHONUNBUFFERED TRUE

# Run the web service on container startup. Here we use the gunicorn webserver
ENTRYPOINT ["gunicorn", "--config", "gunicorn_config.py", "waste_d.wsgi:application"]