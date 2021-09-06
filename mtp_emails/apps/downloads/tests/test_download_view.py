from http import HTTPStatus
import io
import logging
from unittest import mock

from botocore.exceptions import ClientError
from django.http import StreamingHttpResponse
from django.test import SimpleTestCase, override_settings
from django.urls import reverse
from mtp_common.s3_bucket import generate_upload_path
from mtp_common.test_utils import silence_logger

from downloads.views import get_s3_bucket_client


def download_view_url(bucket_path):
    return reverse('download', kwargs={'bucket_path': bucket_path})


def fake_bucket_path(filename):
    return generate_upload_path('test/folder', filename)


def mock_csv_response(mock_s3_bucket_client):
    mock_stream_response = StreamingHttpResponse(
        streaming_content=io.BytesIO(b'prisoner_name,prisoner_number\nJOHN HALLS,A1409AE'),
        content_type='text/csv',
    )
    mock_s3_bucket_client().download_as_streaming_response.return_value = mock_stream_response


@override_settings(EMAILS_URL='http://localhost:8006')
class DownloadViewTestCase(SimpleTestCase):
    def setUp(self):
        super().setUp()
        get_s3_bucket_client.cache_clear()

    @mock.patch('downloads.views.S3BucketClient')
    def test_download(self, mock_s3_bucket_client):
        mock_csv_response(mock_s3_bucket_client)

        filename = 'names.csv'
        response = self.client.get(download_view_url(fake_bucket_path(filename)))
        self.assertContains(response, b'JOHN HALLS', status_code=HTTPStatus.OK)
        self.assertEqual(response['Content-Disposition'], f'attachment; filename="{filename}"')

    @mock.patch('downloads.views.S3BucketClient')
    def test_object_not_found(self, mock_s3_bucket_client):
        mock_s3_bucket_client().download_as_streaming_response.side_effect = ClientError({
            'Error': {
                'Code': 'NoSuchKey',
                'Message': 'Object not found',
            }
        }, 'GetObject')

        filename = 'not-found.csv'
        with silence_logger(name='django.request', level=logging.ERROR):
            response = self.client.get(download_view_url(fake_bucket_path(filename)))
        self.assertNotContains(response, b'JOHN HALLS', status_code=HTTPStatus.NOT_FOUND)
