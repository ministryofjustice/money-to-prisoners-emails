from http import HTTPStatus

from django.conf import settings
from django.http import HttpResponse, HttpRequest
from django.urls import path
from django.utils.crypto import constant_time_compare
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View


class InvalidRequest(Exception):
    pass


class NotifyCallbackView(View):
    def post(self, request):
        try:
            self.validate_request()
        except InvalidRequest as e:
            return HttpResponse(
                f'Invalid request: {e}',
                content_type='text/plain',
                status=HTTPStatus.BAD_REQUEST,
            )
        return HttpResponse(b'', status=HTTPStatus.NO_CONTENT)

    def validate_request(self):
        request: HttpRequest = self.request
        if not request.is_secure():
            raise InvalidRequest('Insecure connection')
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            raise InvalidRequest('Missing authorisation bearer token')
        bearer_token = auth_header[len('Bearer '):]
        if not constant_time_compare(bearer_token, settings.GOVUK_NOTIFY_CALLBACKS_BEARER_TOKEN):
            raise InvalidRequest('Invalid bearer token')


urlpatterns = [
    path('notify-callbacks/', csrf_exempt(NotifyCallbackView.as_view()), name='callbacks'),
]
