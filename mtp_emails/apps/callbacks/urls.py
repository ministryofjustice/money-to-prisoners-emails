import enum
import json
from http import HTTPStatus

from django.conf import settings
from django.http import HttpResponse, HttpRequest
from django.urls import path
from django.utils.crypto import constant_time_compare
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View


class InvalidRequest(Exception):
    pass


class CallbackType(enum.Enum):
    """
    Defined the fields GOV.UK Notify will include in a callback.
    NB: lists of fields are not exhaustive – includes only fields used to distinguish between callback types
    """
    delivery_receipt = ('id', 'reference', 'to', 'status', 'notification_type', 'sent_at', 'template_id')
    received_text_message = ('id', 'source_number', 'destination_number', 'message', 'date_received')

    @classmethod
    def get_payload_type(cls, payload):
        for callback_type in cls:
            if all(field in payload for field in callback_type.value):
                return callback_type


class NotifyCallbackView(View):
    def post(self, request):
        try:
            self.validate_request()
            callback_type, payload = self.parse_callback()
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

    def parse_callback(self) -> tuple:
        request: HttpRequest = self.request
        if request.content_type != 'application/json':
            raise InvalidRequest('Invalid content type')
        try:
            payload = json.loads(request.body)
            if not isinstance(payload, dict):
                raise TypeError
        except (ValueError, TypeError):
            raise InvalidRequest('Invalid JSON payload')
        callback_type = CallbackType.get_payload_type(payload)
        if not callback_type:
            raise InvalidRequest('JSON payload is not a known callback type')
        return callback_type, payload


urlpatterns = [
    path('notify-callbacks/', csrf_exempt(NotifyCallbackView.as_view()), name='callbacks'),
]
