# Use an official lightweight Python image.
# https://hub.docker.com/_/python
FROM python:3.8-slim AS compile-image

ENV APP_HOME /wasted_django
WORKDIR $APP_HOME

# Copy local code to the container image.
COPY setup.py .

# Install packages needed by dependencies.
RUN apt-get update && apt-get -y install default-libmysqlclient-dev build-essential

# Install dependencies.
RUN pip install --user -e .


FROM python:3.8-slim AS build-image

ENV APP_HOME /wasted_django
WORKDIR $APP_HOME

# Service must listen to $PORT environment variable.
# This default value facilitates local development.
ENV PORT 8000

# Setting this ensures print statements and log messages
# promptly appear in Cloud Logging.
ENV PYTHONUNBUFFERED TRUE

# Security: Non-root execution of gunicorn
RUN adduser --disabled-password --uid 999 --gecos "App User" app-user

# Copy pre-compiled stuff
COPY --from=compile-image /root/.local /home/app-user/.local
RUN chmod -R a+r /home/app-user/.local/lib/python3.8/site-packages/ ; find /home/app-user/.local/lib/python3.8/site-packages/ -type d -exec chmod a+x {} \;
#COPY --from=compile-image /usr/local/lib/python3.8/site-packages /usr/local/lib/python3.8/
ENV PATH=/home/app-user/.local/bin:$PATH

# Copy local code to the container image.
COPY wasted_project wasted_project/
COPY waste_d waste_d/
COPY static .
COPY manage.py .
COPY gunicorn_config.py .
COPY django_cloud_tasks django_cloud_tasks/

# Security: Non-root execution of gunicorn
USER app-user

# Run the web service on container startup. Here we use the gunicorn webserver
ENTRYPOINT ["gunicorn", "--config", "gunicorn_config.py", "wasted_project.wsgi:application"]