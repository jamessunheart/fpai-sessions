"""Operator boundary for multi-user Sunheart Brain paths."""

from __future__ import annotations

from functools import wraps


OPERATOR_USER_ID = "james"


class PermissionDenied(Exception):
    """Raised when a tenant attempts an operator-only operation."""


def is_operator(user_id: str) -> bool:
    return str(user_id or "") == OPERATOR_USER_ID


def operator_only(func):
    """Guard functions that may only run in James's operator namespace.

    The wrapped function must receive ``user_id`` as a keyword argument or as
    its first positional argument.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        user_id = kwargs.get("user_id")
        if user_id is None and args:
            user_id = args[0]
        if not is_operator(str(user_id or "")):
            raise PermissionDenied("operator-only action")
        return func(*args, **kwargs)

    return wrapper
