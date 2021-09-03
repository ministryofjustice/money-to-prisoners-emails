import functools
import logging

from botocore.exceptions import ClientError
from django.http import Http404
from django.urls.conf import re_path
from mtp_common.s3_bucket import S3BucketClient, S3BucketError, parse_download_token

logger = logging.getLogger('mtp')


@functools.lru_cache()
def get_s3_bucket_client():
    try:
        return S3BucketClient()
    except S3BucketError:
        logger.exception('S3 bucket client error')
        raise


def get_bucket_path(download_token):
    try:
        return parse_download_token(download_token)
    except ValueError:
        # invalid token, therefore nothing will be revealed
        raise Http404


def get_download_stream_response(bucket_path):
    try:
        return get_s3_bucket_client().download_stream(bucket_path)
    except ClientError as e:
        if e.response.get('Error', {}).get('Code') == 'NoSuchKey':
            # object not found in S3
            raise Http404
        logger.exception('S3 download error')
        raise


def download_view(request, download_token):
    bucket_path = get_bucket_path(download_token)
    filename = bucket_path.rsplit('/', 1)[-1]
    response = get_download_stream_response(bucket_path)
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


urlpatterns = [
    re_path(r'^download/(?P<download_token>.+)$', download_view, name='download'),
]
