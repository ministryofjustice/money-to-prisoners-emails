from django.urls import path
from django.views.decorators.csrf import csrf_exempt

from callbacks.views import NotifyCallbackView

urlpatterns = [
    path('notify-callbacks/', csrf_exempt(NotifyCallbackView.as_view()), name='callbacks'),
]
