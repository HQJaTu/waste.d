import os

# Run the web service on container startup. Here we use the gunicorn
# webserver, with one worker process and 8 threads.
# For environments with multiple CPU cores, increase the number of workers
# to be equal to the cores available.
port = 8000 # See: Dockerfile PORT=
bind = "0.0.0.0:%d" % port
workers = 1
threads = 8
timeout = 0