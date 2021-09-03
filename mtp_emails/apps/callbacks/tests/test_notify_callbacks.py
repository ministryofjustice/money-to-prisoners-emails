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

    def test_callback_must_be_posted(self):
        with silence_logger(name='django.request', level=logging.ERROR):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)
        self.assertIn('POST', response.get('Allow'))

    def assertRejectedCallback(self, response):  # noqa: N802
        self.assertContains(response, 'Invalid request', status_code=HTTPStatus.BAD_REQUEST)

    def assertAcceptedCallback(self, response):  # noqa: N802
        self.assertNotContains(response, 'Invalid request', status_code=HTTPStatus.NO_CONTENT)
        self.assertEqual(response.content, b'')

    @mock.patch.object(HttpRequest, 'is_secure')
    def test_insecure_callback_rejected(self, mock_request_is_secure):
        mock_request_is_secure.return_value = False

        with silence_logger(name='django.request', level=logging.ERROR):
            response = self.client.post(self.url, HTTP_AUTHORIZATION='Bearer 0000111122223333')
        self.assertRejectedCallback(response)

    @mock.patch.object(HttpRequest, 'is_secure')
    def test_secure_callback_with_missing_token_rejected(self, mock_request_is_secure):
        mock_request_is_secure.return_value = True

        with silence_logger(name='django.request', level=logging.ERROR):
            response = self.client.post(self.url)
        self.assertRejectedCallback(response)

    @mock.patch.object(HttpRequest, 'is_secure')
    def test_secure_callback_with_invalid_token_rejected(self, mock_request_is_secure):
        mock_request_is_secure.return_value = True

        with silence_logger(name='django.request', level=logging.ERROR):
            response = self.client.post(self.url, HTTP_AUTHORIZATION='Bearer wrong-token')
        self.assertRejectedCallback(response)

    @mock.patch.object(HttpRequest, 'is_secure')
    def test_secure_callback_with_valid_token_accepted(self, mock_request_is_secure):
        mock_request_is_secure.return_value = True

        response = self.client.post(self.url, HTTP_AUTHORIZATION='Bearer 0000111122223333')
        self.assertAcceptedCallback(response)
