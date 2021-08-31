from http import HTTPStatus
from django.test import SimpleTestCase
from django.urls import reverse


class CallbacksTestCase(SimpleTestCase):

    def test_callbacks(self):
        url = reverse('callbacks')
        response = self.client.get(url)

        self.assertEqual(HTTPStatus.OK, response.status_code)
