from http import HTTPStatus
import io
import logging
import traceback
from unittest import mock
from datetime import timedelta
from email.utils import format_datetime

from botocore.exceptions import ClientError, EndpointConnectionError
from django.http import StreamingHttpResponse
from django.test import SimpleTestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import override as override_language
from mtp_common.private_estate_downloads import PREFIX, issue_token
from mtp_common.s3_bucket import generate_upload_path
from mtp_common.s3_bucket import S3BucketError
from mtp_common.test_utils import silence_logger

from downloads.views import get_s3_bucket_client


def download_view_url(bucket_path):
    return reverse('download', kwargs={'bucket_path': bucket_path})


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
        response = self.client.get(download_view_url(generate_upload_path('emails/2021', filename)))
        self.assertContains(response, b'JOHN HALLS', status_code=HTTPStatus.OK)
        self.assertEqual(response['Content-Disposition'], f'attachment; filename="{filename}"')

    @mock.patch('downloads.views.S3BucketClient')
    def test_download_fails_outside_of_emails_namespace(self, mock_s3_bucket_client):
        mock_csv_response(mock_s3_bucket_client)

        filename = 'names.csv'
        with silence_logger(name='django.request', level=logging.ERROR):
            response = self.client.get(download_view_url(generate_upload_path('backups/2021', filename)))
        self.assertNotContains(response, b'JOHN HALLS', status_code=HTTPStatus.NOT_FOUND)

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
            response = self.client.get(download_view_url(generate_upload_path('emails/2021', filename)))
        self.assertContains(response, 'Page not found', status_code=HTTPStatus.NOT_FOUND)


@override_settings(PRIVATE_ESTATE_DOWNLOAD_SIGNING_KEY='test-signing-key',
                   PRIVATE_ESTATE_DOWNLOAD_LIFETIME_SECONDS=28 * 86400)
class PrivateEstateDownloadViewTestCase(SimpleTestCase):
    path = PREFIX + '2026-11-13/PR1/random/payment.csv'

    def setUp(self):
        super().setUp()
        get_s3_bucket_client.cache_clear()

    @mock.patch('downloads.views.S3BucketClient')
    def test_signed_download_logs_link_identifier_and_source(self, mock_s3):
        mock_csv_response(mock_s3)
        token = issue_token(self.path, 'test-signing-key', 60)
        with self.assertLogs('mtp', level='INFO') as logs:
            response = self.client.get(reverse('private-download'), {'token': token},
                                       HTTP_X_REAL_IP='192.0.2.1')
        self.assertContains(response, b'JOHN HALLS')
        self.assertIn('source_ip=192.0.2.1', logs.output[0])
        self.assertIn('peer_ip=127.0.0.1', logs.output[0])
        self.assertIn('link_id=', logs.output[0])
        self.assertNotIn(token, logs.output[0])
        self.assertEqual(response['Cache-Control'], 'no-store')
        self.assertEqual(response['Referrer-Policy'], 'no-referrer')
        self.assertEqual(response['Content-Disposition'], 'attachment; filename="payment.csv"')
        mock_s3().download_as_streaming_response.assert_called_once_with(self.path)

    @mock.patch('downloads.views.S3BucketClient')
    def test_malformed_ip_header_is_not_written_to_logs(self, mock_s3):
        mock_csv_response(mock_s3)
        token = issue_token(self.path, 'test-signing-key', 60)
        with self.assertLogs('mtp', level='INFO') as logs:
            self.client.get(reverse('private-download'), {'token': token}, HTTP_X_REAL_IP='invalid-address')
        self.assertIn('source_ip=unknown', logs.output[0])
        self.assertIn('peer_ip=127.0.0.1', logs.output[0])
        self.assertNotIn('invalid-address', logs.output[0])

    @mock.patch('downloads.views.S3BucketClient')
    def test_source_falls_back_to_peer_when_header_is_absent(self, mock_s3):
        mock_csv_response(mock_s3)
        token = issue_token(self.path, 'test-signing-key', 60)
        with self.assertLogs('mtp', level='INFO') as logs:
            self.client.get(reverse('private-download'), {'token': token}, REMOTE_ADDR='2001:db8::1')
        self.assertIn('source_ip=2001:db8::1', logs.output[0])
        self.assertIn('peer_ip=2001:db8::1', logs.output[0])

    @mock.patch('downloads.views.S3BucketClient')
    def test_emailed_link_redirects_to_a_working_download(self, mock_s3):
        mock_csv_response(mock_s3)
        token = issue_token(self.path, 'test-signing-key', 60)
        response = self.client.get('/download-private', {'token': token}, follow=True)
        self.assertContains(response, b'JOHN HALLS')

    def test_signed_link_redirect_does_not_send_referrer(self):
        response = self.client.get('/download-private', {'token': 'synthetic-token'})
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertEqual(response['Referrer-Policy'], 'no-referrer')
        self.assertEqual(response['Cache-Control'], 'no-store')

    def test_invalid_welsh_link_has_privacy_headers(self):
        with override_language('en-gb'), silence_logger(name='django.request', level=logging.ERROR):
            response = self.client.get('/cy/download-private', {'token': 'invalid'})
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertEqual(response['Referrer-Policy'], 'no-referrer')
        self.assertEqual(response['Cache-Control'], 'no-store')

    def test_other_responses_keep_their_existing_referrer_policy(self):
        response = self.client.get('/robots.txt')
        self.assertEqual(response['Referrer-Policy'], 'same-origin')

    @mock.patch('downloads.views.S3BucketClient')
    def test_unsigned_tampered_and_expired_links_do_not_reach_s3(self, mock_s3):
        token = issue_token(self.path, 'test-signing-key', 1)
        with mock.patch('mtp_common.private_estate_downloads.time.time', return_value=9999999999):
            for url, params in ((download_view_url(self.path), {}),
                                (reverse('private-download'), {}),
                                (reverse('private-download'), {'token': token + 'x'}),
                                (reverse('private-download'), {'token': token})):
                self.assertEqual(self.client.get(url, params).status_code, HTTPStatus.NOT_FOUND)
        mock_s3.assert_not_called()

    @mock.patch('downloads.views.S3BucketClient')
    def test_legacy_path_cannot_traverse_to_signed_objects(self, mock_s3):
        target = 'private-estate-credits-v2/2026-11-13/PR1/random/payment.csv'
        for path in (f'emails/../{target}', f'emails/./../{target}', f'emails/..\\{target}'):
            with self.subTest(path=path):
                response = self.client.get(download_view_url(path))
                self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertEqual(self.client.get(f'/en-gb/download/emails/%2E%2E/{target}').status_code,
                         HTTPStatus.NOT_FOUND)
        mock_s3.assert_not_called()

    @mock.patch('downloads.views.S3BucketClient')
    def test_legacy_private_estate_links_expire_using_object_creation_time(self, mock_s3):
        legacy_path = 'emails/private-estate-credits/2026-11-13/PR1/random/payment.csv'
        mock_csv_response(mock_s3)
        stream = mock_s3().download_as_streaming_response.return_value
        stream['Last-Modified'] = format_datetime(timezone.now() - timedelta(days=69))
        response = self.client.get(download_view_url(legacy_path))
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response['Referrer-Policy'], 'no-referrer')
        stream['Last-Modified'] = format_datetime(timezone.now() - timedelta(days=71))
        with self.assertLogs('django.request', level='WARNING') as logs:
            self.assertEqual(self.client.get(download_view_url(legacy_path)).status_code, HTTPStatus.NOT_FOUND)
        self.assertNotIn(legacy_path, logs.output[0])
        self.assertIn('Private estate download returned HTTP 404', logs.output[0])

    @mock.patch('downloads.views.S3BucketClient')
    def test_missing_legacy_file_is_not_written_to_error_logs(self, mock_s3):
        mock_s3().download_as_streaming_response.side_effect = ClientError({
            'Error': {'Code': 'NoSuchKey', 'Message': 'Object not found'}
        }, 'GetObject')
        legacy_path = 'emails/private-estate-credits/2026-11-13/PR1/bearer-secret/payment.csv'
        with self.assertLogs('django.request', level='WARNING') as logs:
            self.assertEqual(self.client.get(download_view_url(legacy_path)).status_code, HTTPStatus.NOT_FOUND)
        self.assertNotIn(legacy_path, logs.output[0])

    @mock.patch('downloads.views.S3BucketClient')
    def test_s3_errors_do_not_log_legacy_key(self, mock_s3):
        legacy_path = 'emails/private-estate-credits/2026-11-13/PR1/bearer-secret/payment.csv'
        mock_s3().download_as_streaming_response.side_effect = ClientError({
            'Error': {'Code': 'AccessDenied', 'Message': 'Access to ' + legacy_path + ' denied'}
        }, 'GetObject')
        self.client.raise_request_exception = False
        with self.assertLogs('mtp', level='ERROR') as logs:
            with self.assertLogs('django.request', level='ERROR') as request_logs:
                response = self.client.get(download_view_url(legacy_path))
        self.assertEqual(response.status_code, HTTPStatus.INTERNAL_SERVER_ERROR)
        self.assertNotIn(legacy_path, '\n'.join(logs.output + request_logs.output))
        self.assertIn('AccessDenied', logs.output[0])

    @mock.patch('downloads.views.S3BucketClient')
    def test_s3_connection_errors_do_not_log_legacy_key(self, mock_s3):
        legacy_path = 'emails/private-estate-credits/2026-11-13/PR1/bearer-secret/payment.csv'
        mock_s3().download_as_streaming_response.side_effect = EndpointConnectionError(
            endpoint_url='https://s3.example.test/' + legacy_path,
        )
        self.client.raise_request_exception = False
        with self.assertLogs('mtp', level='ERROR') as logs:
            with self.assertLogs('django.request', level='ERROR') as request_logs:
                response = self.client.get(download_view_url(legacy_path))
        self.assertEqual(response.status_code, HTTPStatus.INTERNAL_SERVER_ERROR)
        self.assertNotIn(legacy_path, '\n'.join(logs.output + request_logs.output))
        self.assertIn('EndpointConnectionError', logs.output[0])

    @mock.patch('downloads.views.S3BucketClient')
    def test_stream_errors_do_not_expose_legacy_key(self, mock_s3):
        legacy_path = 'emails/private-estate-credits/2026-11-13/PR1/bearer-secret/payment.csv'

        def failing_stream():
            yield b'first chunk'
            raise EndpointConnectionError(endpoint_url='https://s3.example.test/' + legacy_path)

        stream = StreamingHttpResponse(failing_stream(), content_type='text/csv')
        stream['Last-Modified'] = format_datetime(timezone.now() - timedelta(days=1))
        mock_s3().download_as_streaming_response.return_value = stream
        response = self.client.get(download_view_url(legacy_path))
        with self.assertLogs('mtp', level='ERROR') as logs:
            try:
                list(response.streaming_content)
                self.fail('Expected stream failure')
            except S3BucketError as e:
                formatted = ''.join(traceback.format_exception(e))
        self.assertNotIn(legacy_path, formatted + '\n'.join(logs.output))
        self.assertIn('EndpointConnectionError', logs.output[0])
