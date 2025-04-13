from celery import Celery
from app import create_app

REDIS_URL = "redis://default:SECha3rfcypwujnEptRBzdwWpI5pqc84@redis-12806.c99.us-east-1-4.ec2.redns.redis-cloud.com:12806"

celery = Celery("tasks", broker=REDIS_URL)

def make_celery(app):
    celery.conf.update(app.config)
    TaskBase = celery.Task

    class ContextTask(TaskBase):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)

    celery.Task = ContextTask
    return celery

app = create_app()
celery = make_celery(app)

@celery.task
def parse_emails():
    from app.email_parser import check_email
    check_email()