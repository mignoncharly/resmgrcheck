"""Dedicated service configuration; disable the version's shared user control socket."""
control_socket_disable=True
workers=1
threads=2
timeout=30
graceful_timeout=30
max_requests=1000
max_requests_jitter=50
accesslog=None
limit_request_line=4094
limit_request_fields=50
limit_request_field_size=4094
