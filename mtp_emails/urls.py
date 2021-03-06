from django.conf import settings
from django.conf.urls import include, url
from django.conf.urls.i18n import i18n_patterns
from django.http import HttpResponse
from django.template.response import TemplateResponse
from django.views.decorators.cache import cache_control
from django.views.generic import RedirectView
from django.views.i18n import JavaScriptCatalog
from moj_irat.views import HealthcheckView, PingJsonView
from mtp_common.metrics.views import metrics_view


urlpatterns = i18n_patterns(
    url(r'^', include('downloads.urls',)),

    url(r'^js-i18n.js$', cache_control(public=True, max_age=86400)(JavaScriptCatalog.as_view()), name='js-i18n'),

    url(r'^404.html$', lambda request: TemplateResponse(request, 'mtp_common/errors/404.html', status=404)),
    url(r'^500.html$', lambda request: TemplateResponse(request, 'mtp_common/errors/500.html', status=500)),
)

urlpatterns += [
    url(r'^', include('callbacks.urls',)),

    url(r'^ping.json$', PingJsonView.as_view(
        build_date_key='APP_BUILD_DATE',
        commit_id_key='APP_GIT_COMMIT',
        version_number_key='APP_BUILD_TAG',
    ), name='ping_json'),
    url(r'^healthcheck.json$', HealthcheckView.as_view(), name='healthcheck_json'),
    url(r'^metrics.txt$', metrics_view, name='prometheus_metrics'),

    url(r'^favicon.ico$', RedirectView.as_view(url=settings.STATIC_URL + 'images/favicon.ico', permanent=True)),
    url(r'^robots.txt$', lambda request: HttpResponse('User-agent: *\nDisallow: /', content_type='text/plain')),
    url(r'^\.well-known/security\.txt$', RedirectView.as_view(
        url='https://security-guidance.service.justice.gov.uk/.well-known/security.txt',
        permanent=True,
    )),
]

handler404 = 'mtp_common.views.page_not_found'
handler500 = 'mtp_common.views.server_error'
handler400 = 'mtp_common.views.bad_request'
