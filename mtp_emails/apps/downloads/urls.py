from django.urls.conf import re_path

from downloads.views import download_view

urlpatterns = [
    re_path(r'^download/(?P<bucket_path>.+)$', download_view, name='download'),
]
