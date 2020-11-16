# Use an official lightweight Python image.
# https://hub.docker.com/_/python
FROM python:3.8-slim

ENV APP_HOME /wasted_django
WORKDIR $APP_HOME

# Copy local code to the container image.
COPY wasted_project wasted_project/
COPY waste_d waste_d/
COPY static .
COPY manage.py .
COPY gunicorn_config.py .
COPY setup.py .

# Install packages needed by dependencies.
RUN apt-get -y install libmysqlclient-dev

# Install dependencies.
RUN pip install install -e .

# Service must listen to $PORT environment variable.
# This default value facilitates local development.
ENV PORT 8000

# Setting this ensures print statements and log messages
# promptly appear in Cloud Logging.
ENV PYTHONUNBUFFERED TRUE

# Security: Non-root execution of gunicorn
RUN adduser --disabled-password --uid 999 app-user
USER app-user

# Run the web service on container startup. Here we use the gunicorn webserver
ENTRYPOINT ["gunicorn", "--config", "gunicorn_config.py", "wasted_project.wsgi:application"]