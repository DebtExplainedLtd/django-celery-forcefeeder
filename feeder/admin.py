import importlib

from django.conf.urls import url
from django.contrib import admin, messages
from django.http import HttpResponseRedirect
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from django import VERSION

if VERSION >= (2, 0):
    from django.urls import reverse
else:
    from django.core.urlresolvers import reverse

from tasks import single_object_task_wrapper


class DocumentAdminTasksMixin(admin.ModelAdmin):
    row_tasks_async = []

    def __init__(self, *args, **kwargs):
        super(DocumentAdminTasksMixin, self).__init__(*args, **kwargs)
        self.verify_task_names()

    def verify_task_names(self):
        # Stealing a little bit of the magical auto-detection from Celery
        from django.apps import apps
        app_names = [config.name for config in apps.get_app_configs()]
        for task_name, task_label in self.row_tasks_async:
            app_name = task_name.split('.')[0]
            assert(app_name in app_names)
            app_tasks = importlib.import_module('%s.tasks' % app_name)
            assert(hasattr(app_tasks, task_name.split('.')[1]))

    def exec_task_view(self, request, object_id, task_name, extra_context=None):
        single_object_task_wrapper.apply_async([task_name, object_id, request.user.id])
        self.message_user(request, 'Task successfully queued', level=messages.SUCCESS)
        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))

    def get_urls(self):
        urls = super(DocumentAdminTasksMixin, self).get_urls()
        # noinspection PyProtectedMember
        exec_task_url_name = '{0}_{1}_exec'.format(self.model._meta.app_label,
                                                  self.model._meta.model_name)
        exec_task_url = url(r'^(\d+)/exec/(\w.+)/$', self.admin_site.admin_view(self.exec_task_view),
                            name=exec_task_url_name)
        return [exec_task_url] + urls

    def get_list_display(self, request):
        list_display = super(DocumentAdminTasksMixin, self).get_list_display(request)
        if self.row_tasks_async:
            list_display += ('registered_tasks',)
        return list_display

    def build_task_link(self, obj, task_name, task_label):
        # noinspection PyProtectedMember
        exec_url_name = 'admin:{0}_{1}_exec'.format(self.model._meta.app_label, self.model._meta.model_name)
        exec_url = reverse(exec_url_name, args=[obj.id, task_name])
        return format_html("<a href='{url}'>{label}</a>", url=exec_url, label=task_label)

    def registered_tasks(self, obj):
        links = [self.build_task_link(obj, task_name, task_label) for (task_name, task_label) in self.row_tasks_async]
        return mark_safe('<div>%s</div>' % ''.join(links))

    registered_tasks.short_description = 'Tasks'
