import functools
import logging

from botocore.exceptions import ClientError
from django.http import Http404
from mtp_common.s3_bucket import S3BucketClient, S3BucketError

logger = logging.getLogger('mtp')


@functools.lru_cache()
def get_s3_bucket_client():
    try:
        return S3BucketClient()
    except S3BucketError:
        logger.exception('S3 bucket client error')
        raise


def download_view(request, bucket_path: str):
    if not bucket_path.startswith('emails/'):
        raise Http404
    filename = bucket_path.rsplit('/', 1)[-1]
    try:
        response = get_s3_bucket_client().download_as_streaming_response(bucket_path)
    except ClientError as e:
        if e.response.get('Error', {}).get('Code') == 'NoSuchKey':
            # object not found in S3
            raise Http404
        logger.exception('S3 download error')
        raise
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
