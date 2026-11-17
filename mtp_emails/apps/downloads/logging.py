import logging


class RedactLegacyDownloadPath(logging.Filter):
    """Keep the old bearer URL out of Django's request-error logs."""

    def filter(self, record):
        request = getattr(record, 'request', None)
        path = getattr(request, 'path', '')
        if '/download/emails/private-estate-credits/' in path:
            record.msg = 'Private estate download returned HTTP %s'
            record.args = (getattr(record, 'status_code', 'unknown'),)
            # The admin email handler includes the entire request when present.
            record.request = None
        return True
