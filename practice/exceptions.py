from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler


class Conflict(APIException):
    status_code = 409
    default_detail = "Conflicto con el estado actual del recurso."
    default_code = "conflict"


def api_exception_handler(exc, context):  # type: ignore[no-untyped-def]
    response = exception_handler(exc, context)
    if response is not None:
        detail = response.data.get("detail") if isinstance(response.data, dict) else response.data
        response.data = {"error": {"status": response.status_code, "detail": detail}}
    return response
