from django.urls.conf import re_path

from downloads.views import download_view, private_download_view

urlpatterns = [
    re_path(r'^download-private$', private_download_view, name='private-download'),
    re_path(r'^download/(?P<bucket_path>.+)$', download_view, name='download'),
]
