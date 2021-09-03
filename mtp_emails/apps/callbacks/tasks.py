import logging

from mtp_common.spooling import spoolable

logger = logging.getLogger('mtp')


@spoolable(body_params=('payload',))
def handle_callback_payload(callback_type_name: str, payload: dict):
    from callbacks.urls import CallbackType

    print(callback_type_name, payload)  # TODO: remove once some samples have been collected

    callback_type = CallbackType[callback_type_name]
    if callback_type == CallbackType.delivery_receipt:
        logger.info(
            'GOV.UK Notify delivery receipt %(id)s status=%(status)s ref=%(reference)s',
            payload,
        )
    elif callback_type == CallbackType.received_text_message:
        logger.info(
            'GOV.UK Notify received text message %(id)s source_number=%(source_number)s message=%(message)s',
            payload,
        )
    else:
        logger.error('Unhandled GOV.UK Notify type %s', callback_type.name)
