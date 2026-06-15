import os

# Gunicorn configuration file

# Server socket
bind = "0.0.0.0:80"

# Worker processes
workers = int(os.environ.get('GUNICORN_PROCESSES', '2'))
worker_class = "uvicorn.workers.UvicornWorker"

# Logging
loglevel = os.environ.get('GUNICORN_LOGLEVEL', 'info')
accesslog = '-'  # Log to stdout
errorlog = '-'   # Log to stderr

# Process naming
proc_name = "ssp-search-service"
