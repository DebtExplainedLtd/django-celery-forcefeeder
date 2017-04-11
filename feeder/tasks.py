import importlib

from celery import shared_task
from django.contrib.auth.models import User
from django.core.mail import send_mail


@shared_task
def single_object_task_wrapper(task_name, object_id, user_id):
    app_tasks = importlib.import_module('%s.tasks' % task_name.split('.')[0])
    task = getattr(app_tasks, task_name.split('.')[1])
    user = User.objects.get(id=user_id)
    try:
        task(object_id)
    except Exception:
        send_mail('Django Admin Task Failure',
                  'Failure when attempting to run the task %s' % task_name,
                  'software@debtexplained.com',
                  [user.email])
        raise
    else:
        # Email success message
        send_mail('Django Admin Task Success',
                  'Task complete - %s' % task_name,
                  'software@debtexplained.com',
                  [user.email])
