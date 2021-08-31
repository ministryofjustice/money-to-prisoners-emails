import io

from django.http import HttpResponse
from django.urls import path


def download(request, id, filename):
    content_type = 'text/plain'
    file = io.StringIO('TODO: This is just a placeholder/test')

    response = HttpResponse(file, content_type=content_type)
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    return response


urlpatterns = [
    path('download/<str:id>/<str:filename>/', download, name='download'),
]
