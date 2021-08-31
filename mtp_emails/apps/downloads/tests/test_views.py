from http import HTTPStatus
from django.test import SimpleTestCase
from django.urls import reverse


class DownloadCallbacksTestCase(SimpleTestCase):

    def test_download(self):
        filename = 'test.txt'
        url = reverse('download', kwargs={'id': 'TODO', 'filename': filename})

        response = self.client.get(url)

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.content, b'TODO: This is just a placeholder/test')

        disposition = response._headers['content-disposition'][1]

        self.assertEqual(disposition, f'attachment; filename="{filename}"')
