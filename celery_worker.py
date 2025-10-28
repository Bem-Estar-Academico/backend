import ssl
from celery import Celery

celery_app = Celery(
    "tasks",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0",
    include=["app.ocr_processing.tasks"],
)
celery_app.conf.broker_transport_options = {
    'ssl_cert_reqs': ssl.CERT_NONE,
}
celery_app.conf.redis_backend_transport_options = {
    'ssl_cert_reqs': ssl.CERT_NONE,
}

celery_app.conf.update(
    task_track_started=True,
)
