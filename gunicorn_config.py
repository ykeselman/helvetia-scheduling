import multiprocessing

from common_utils import CONFIG

cpus = multiprocessing.cpu_count()

WEB_PORT = CONFIG['WEB_PORT']
bind = f"127.0.0.1:{WEB_PORT}"
worker_class = 'gthread'

# workers = (cpus * 2) +1
workers = cpus

# Workers silent for more than this many seconds are killed and restarted.
timeout = 30

# The number of seconds to wait for requests on a Keep-Alive connection.
keepalive = 5
