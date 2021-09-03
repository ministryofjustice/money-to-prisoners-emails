from http import HTTPStatus
import io
import logging
from unittest import mock

from botocore.exceptions import ClientError
from django.http import StreamingHttpResponse
from django.test import SimpleTestCase, override_settings
from django.urls import reverse
from mtp_common.s3_bucket import make_download_token
from mtp_common.test_utils import silence_logger

from downloads.urls import get_s3_bucket_client


def download_view_url(download_token):
    return reverse('download', kwargs={'download_token': download_token})


def fake_download_token(filename):
    return make_download_token('test/folder', filename)['download_token']


def mock_csv_response(mock_s3_bucket_client):
    mock_stream_response = StreamingHttpResponse(
        streaming_content=io.BytesIO(b'prisoner_name,prisoner_number\nJOHN HALLS,A1409AE'),
        content_type='text/csv',
    )
    mock_s3_bucket_client().download_stream.return_value = mock_stream_response


@override_settings(S3_BUCKET_SIGNING_KEY='0000111122223333', EMAILS_URL='http://localhost:8006')
class DownloadViewTestCase(SimpleTestCase):
    def setUp(self):
        super().setUp()
        get_s3_bucket_client.cache_clear()

    @mock.patch('downloads.urls.S3BucketClient')
    def test_download(self, mock_s3_bucket_client):
        mock_csv_response(mock_s3_bucket_client)

        filename = 'names.csv'
        response = self.client.get(download_view_url(fake_download_token(filename)))
        self.assertContains(response, b'JOHN HALLS', status_code=HTTPStatus.OK)
        self.assertEqual(response['Content-Disposition'], f'attachment; filename="{filename}"')

    @mock.patch('downloads.urls.S3BucketClient')
    def test_invalid_download_token(self, mock_s3_bucket_client):
        mock_csv_response(mock_s3_bucket_client)

        filename = 'names.csv'
        with silence_logger(name='django.request', level=logging.ERROR):
            response = self.client.get(download_view_url(f'test/folder/invalid-token/{filename}'))
        self.assertNotContains(response, b'JOHN HALLS', status_code=HTTPStatus.NOT_FOUND)

    @mock.patch('downloads.urls.S3BucketClient')
    def test_object_not_found(self, mock_s3_bucket_client):
        mock_s3_bucket_client().download_stream.side_effect = ClientError({
            'Error': {
                'Code': 'NoSuchKey',
                'Message': 'Object not found',
            }
        }, 'GetObject')

        filename = 'not-found.csv'
        with silence_logger(name='django.request', level=logging.ERROR):
            response = self.client.get(download_view_url(fake_download_token(filename)))
        self.assertNotContains(response, b'JOHN HALLS', status_code=HTTPStatus.NOT_FOUND)
