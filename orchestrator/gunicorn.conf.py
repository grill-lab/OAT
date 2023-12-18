import multiprocessing

bind = '0.0.0.0:8000'
workers = multiprocessing.cpu_count() * 2 + 1
timeout = 12

worker_connections = 256
backlog = 128

worker_class = 'sync'
