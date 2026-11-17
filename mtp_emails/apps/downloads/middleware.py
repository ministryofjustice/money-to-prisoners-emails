import re


PRIVATE_DOWNLOAD_PATH = re.compile(
    r'^/(?:en-gb/|cy/)?(?:download-private(?:/|$)|download/emails/private-estate-credits/)'
)


class PrivateDownloadReferrerPolicyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if PRIVATE_DOWNLOAD_PATH.match(request.path_info):
            response['Referrer-Policy'] = 'no-referrer'
            response['Cache-Control'] = 'no-store'
        return response
