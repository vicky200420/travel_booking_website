# Gunicorn configuration for TravelBooking.
import os

bind = "0.0.0.0:8000"
workers = int(os.getenv("GUNICORN_WORKERS", "3"))
worker_tmp_dir = "/dev/shm"
timeout = int(os.getenv("GUNICORN_TIMEOUT", "120"))
graceful_timeout = 30
accesslog = "-"
errorlog = "-"
loglevel = "info"
