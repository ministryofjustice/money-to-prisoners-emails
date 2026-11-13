import functools
import hashlib
import ipaddress
import logging
import re
from datetime import timedelta
from email.utils import parsedate_to_datetime

from botocore.exceptions import BotoCoreError, ClientError
from django.conf import settings
from django.core import signing
from django.http import Http404
from django.utils import timezone
from mtp_common.private_estate_downloads import LEGACY_LIFETIME_SECONDS, PREFIX, read_token
from mtp_common.s3_bucket import S3BucketClient, S3BucketError

logger = logging.getLogger('mtp')
LEGACY_PRIVATE_ESTATE_LIFETIME = timedelta(seconds=LEGACY_LIFETIME_SECONDS)


@functools.lru_cache()
def get_s3_bucket_client():
    try:
        return S3BucketClient()
    except S3BucketError:
        logger.exception('S3 bucket client error')
        raise


def download_view(request, bucket_path: str):
    if (not bucket_path.startswith('emails/') or '\\' in bucket_path
            or any(part in ('.', '..') for part in bucket_path.split('/'))):
        raise Http404
    response = download_object(bucket_path)
    if bucket_path.startswith('emails/private-estate-credits/'):
        try:
            modified = parsedate_to_datetime(response['Last-Modified'])
            expired = timezone.now() >= modified + LEGACY_PRIVATE_ESTATE_LIFETIME
        except (KeyError, TypeError, ValueError, OverflowError):
            expired = True
        if expired:
            response.close()
            raise Http404
        log_download(request, bucket_path)
    return prepare_response(response, bucket_path)


def private_download_view(request):
    token = request.GET.get('token', '')
    try:
        bucket_path = read_token(token, settings.PRIVATE_ESTATE_DOWNLOAD_SIGNING_KEY)
    except signing.BadSignature:
        raise Http404
    response = download_object(bucket_path)
    log_download(request, token)
    return prepare_response(response, bucket_path)


def log_download(request, identifier):
    peer = request.META.get('REMOTE_ADDR', '')
    source = request.META.get('HTTP_X_REAL_IP') or peer
    identifier_hash = hashlib.sha256(identifier.encode('utf-8')).hexdigest()
    logger.info('Private estate download started link_id=%s source_ip=%s peer_ip=%s',
                identifier_hash, format_ip(source), format_ip(peer))


def format_ip(value):
    try:
        return str(ipaddress.ip_address(value))
    except (TypeError, ValueError):
        return 'unknown'


def download_object(bucket_path):
    try:
        response = get_s3_bucket_client().download_as_streaming_response(bucket_path)
    except ClientError as e:
        if e.response.get('Error', {}).get('Code') == 'NoSuchKey':
            # object not found in S3
            raise Http404
        # S3 error messages can include the object key, which is itself a bearer
        # credential for legacy downloads. Keep only a bounded error code.
        code = e.response.get('Error', {}).get('Code', '')
        code = code if isinstance(code, str) and re.fullmatch(r'[A-Za-z0-9]{1,64}', code) else 'unknown'
        logger.error('S3 download error: %s', code)
        raise S3BucketError('S3 download failed') from None
    except BotoCoreError as e:
        # Connection and timeout exceptions can include the complete S3 URL.
        logger.error('S3 download error: %s', type(e).__name__)
        raise S3BucketError('S3 download failed') from None
    return response


def prepare_response(response, bucket_path):
    filename = bucket_path.rsplit('/', 1)[-1]
    if bucket_path.startswith((PREFIX, 'emails/private-estate-credits/')):
        response.streaming_content = safe_download_stream(response.streaming_content)
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response['Cache-Control'] = 'no-store'
    response['Referrer-Policy'] = 'no-referrer'
    return response


def safe_download_stream(stream):
    try:
        yield from stream
    except Exception as e:
        # Body reads happen after the view returns; an exception can contain the S3 key.
        logger.error('S3 download stream error: %s', type(e).__name__)
        raise S3BucketError('S3 download stream failed') from None
