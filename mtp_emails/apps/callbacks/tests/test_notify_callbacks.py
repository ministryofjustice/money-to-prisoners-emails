from http import HTTPStatus
import logging
from unittest import mock

from django.http import HttpRequest
from django.test import SimpleTestCase, override_settings
from django.urls import reverse_lazy
from mtp_common.test_utils import silence_logger


@override_settings(GOVUK_NOTIFY_CALLBACKS_BEARER_TOKEN='0000111122223333')
class NotifyCallbacksTestCase(SimpleTestCase):
    url = reverse_lazy('callbacks')

    valid_delivery_receipt_payload = {
        # NB: this is not an exhaustive set of valid fields
        'id': '11111-22222', 'sent_at': '2021-09-03T12:15:30Z',
        'notification_type': 'email', 'template_id': '11',
        'reference': 'transaction-111112',
        'to': 'user@outside.local',
        'status': 'delivered',
    }
    valid_received_text_message_payload = {
        'id': '11111-22222', 'date_received': '2021-09-03T12:15:30Z',
        'source_number': '07000000000', 'destination_number': '07000000001', 'message': 'How do I sign in?',
    }

    def assertRejectedCallback(self, response, expected_error):  # noqa: N802
        self.assertContains(response, expected_error, status_code=HTTPStatus.BAD_REQUEST)

    def assertAcceptedCallback(self, response):  # noqa: N802
        self.assertNotContains(response, 'Invalid request', status_code=HTTPStatus.NO_CONTENT)
        self.assertEqual(response.content, b'')

    @mock.patch.object(HttpRequest, 'is_secure')
    def test_callback_must_be_posted(self, mock_request_is_secure):
        mock_request_is_secure.return_value = True

        with silence_logger(name='django.request', level=logging.ERROR):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)
        self.assertIn('POST', response.get('Allow'))

    @mock.patch.object(HttpRequest, 'is_secure')
    def test_insecure_callback_rejected(self, mock_request_is_secure):
        mock_request_is_secure.return_value = False

        with silence_logger(name='django.request', level=logging.ERROR):
            response = self.client.post(self.url, HTTP_AUTHORIZATION='Bearer 0000111122223333')
        self.assertRejectedCallback(response, 'Insecure connection')

    @mock.patch.object(HttpRequest, 'is_secure')
    def test_secure_callback_with_missing_token_rejected(self, mock_request_is_secure):
        mock_request_is_secure.return_value = True

        with silence_logger(name='django.request', level=logging.ERROR):
            response = self.client.post(self.url)
        self.assertRejectedCallback(response, 'Missing authorisation bearer token')

    @mock.patch.object(HttpRequest, 'is_secure')
    def test_secure_callback_with_invalid_token_rejected(self, mock_request_is_secure):
        mock_request_is_secure.return_value = True

        with silence_logger(name='django.request', level=logging.ERROR):
            response = self.client.post(self.url, HTTP_AUTHORIZATION='Bearer wrong-token')
        self.assertRejectedCallback(response, 'Invalid bearer token')

    @mock.patch.object(HttpRequest, 'is_secure')
    def test_secure_callback_with_invalid_content_type_rejected(self, mock_request_is_secure):
        mock_request_is_secure.return_value = True

        with silence_logger(name='django.request', level=logging.ERROR):
            response = self.client.post(
                self.url, data=self.valid_delivery_receipt_payload,
                HTTP_AUTHORIZATION='Bearer 0000111122223333',
            )
        self.assertRejectedCallback(response, 'Invalid content type')

    @mock.patch.object(HttpRequest, 'is_secure')
    def test_secure_callback_with_invalid_payload_encoding_rejected(self, mock_request_is_secure):
        mock_request_is_secure.return_value = True

        with silence_logger(name='django.request', level=logging.ERROR):
            response = self.client.post(
                self.url, data='id=11111-22222',
                content_type='application/json',
                HTTP_AUTHORIZATION='Bearer 0000111122223333',
            )
        self.assertRejectedCallback(response, 'Invalid JSON payload')

    @mock.patch.object(HttpRequest, 'is_secure')
    def test_secure_callback_with_invalid_json_payload_rejected(self, mock_request_is_secure):
        mock_request_is_secure.return_value = True

        with silence_logger(name='django.request', level=logging.ERROR):
            response = self.client.post(
                self.url, data={'id': '11111-22222'},
                content_type='application/json',
                HTTP_AUTHORIZATION='Bearer 0000111122223333',
            )
        self.assertRejectedCallback(response, 'JSON payload is not a known callback type')

    @mock.patch('callbacks.tasks.logger')
    @mock.patch.object(HttpRequest, 'is_secure')
    def test_secure_delivery_receipt_with_valid_token_accepted(self, mock_request_is_secure, mock_logger):
        mock_request_is_secure.return_value = True

        response = self.client.post(
            self.url, data=self.valid_delivery_receipt_payload,
            content_type='application/json',
            HTTP_AUTHORIZATION='Bearer 0000111122223333',
        )
        self.assertAcceptedCallback(response)
        self.assertEqual(mock_logger.info.call_count, 1)

    @mock.patch('callbacks.tasks.logger')
    @mock.patch.object(HttpRequest, 'is_secure')
    def test_secure_received_text_message_with_valid_token_accepted(self, mock_request_is_secure, mock_logger):
        mock_request_is_secure.return_value = True

        response = self.client.post(
            self.url, data=self.valid_received_text_message_payload,
            content_type='application/json',
            HTTP_AUTHORIZATION='Bearer 0000111122223333',
        )
        self.assertAcceptedCallback(response)
        self.assertEqual(mock_logger.info.call_count, 1)
