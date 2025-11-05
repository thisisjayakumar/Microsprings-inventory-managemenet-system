bind = "127.0.0.1:8000"
workers = 3
user = "www-data"
group = "www-data"
loglevel = "info"
errorlog = "/var/log/gunicorn/error.log"
accesslog = "/var/log/gunicorn/access.log"