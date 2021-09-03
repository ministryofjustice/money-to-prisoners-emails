from http import HTTPStatus
import logging

from django.test import SimpleTestCase
from django.urls import reverse_lazy
from mtp_common.test_utils import silence_logger


class NotifyCallbacksTestCase(SimpleTestCase):
    url = reverse_lazy('callbacks')

    def test_callback_must_be_posted(self):
        with silence_logger(name='django.request', level=logging.ERROR):
            response = self.client.get(self.url)
        self.assertNotContains(response, 'placeholder', status_code=HTTPStatus.METHOD_NOT_ALLOWED)

    def test_callback_accepted(self):
        response = self.client.post(self.url)
        self.assertContains(response, 'placeholder', status_code=HTTPStatus.OK)
