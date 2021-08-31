from django.conf.urls import url
from django.http import HttpResponse


def notify_callbacks(request):
    response = HttpResponse('TODO: This is just a placeholder/test')
    return response


urlpatterns = [
    url(r'^callbacks/$', notify_callbacks, name='callbacks'),
]
