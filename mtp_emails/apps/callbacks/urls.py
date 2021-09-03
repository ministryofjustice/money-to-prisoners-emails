from django.http import HttpResponse
from django.urls import path
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View


class NotifyCallbackView(View):
    def post(self, request):
        return HttpResponse('TODO: This is just a placeholder/test')


urlpatterns = [
    path('notify-callbacks/', csrf_exempt(NotifyCallbackView.as_view()), name='callbacks'),
]
