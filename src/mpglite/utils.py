from .exceptions import SignatureError

import inspect
from contextlib import contextmanager

from collections.abc import Callable


def format_list_with_and(items: list, start="", end="", surround=""):
    """[1, 2, 3] -> \"1, 2 and 3\" """

    item_start = surround
    item_end = surround

    if start:
        item_start = start
    if end:
        item_end = end

    str_items = [item_start + str(i) + item_end for i in items]

    if len(str_items) == 0:
        return ""
    if len(str_items) == 1:
        return str_items[0]

    return ", ".join(str_items[:-1]) + " and " + str_items[-1]


def smart_kwargs(func: Callable | None, **available_data) -> dict:
    """
    Calls func with only the arguments it actually asked for. It returns {} if func is None.
    Raises SignatureError if we don't pass a mandatory argument that the callback func expects.
    """

    if not func:
        return {}

    sig = inspect.signature(func)
    has_kwargs = any(p.kind == p.VAR_KEYWORD for p in sig.parameters.values())

    if has_kwargs:
        # If the function accepts **kwargs, give it everything!
        return available_data

    # Otherwise, filter only what the function specifically asked for
    kwargs = {
        name: value for name, value in available_data.items() if name in sig.parameters
    }

    # Check for missing mandatory parameters
    missed_params = [
        name
        for name, param in sig.parameters.items()
        if param.default is param.empty
        and name not in kwargs
        and param.kind != param.VAR_POSITIONAL  # Ignore *args
        and param.kind != param.VAR_KEYWORD  # Ignore **kwargs
    ]

    if missed_params:
        extra_params = format_list_with_and(missed_params, surround='"')
        provided_params = format_list_with_and(
            list(available_data.keys()), surround='"'
        )

        callback_name = f'"{func.__name__}" ' if hasattr(func, "__name__") else ""
        raise SignatureError(
            f"The provided callback {callback_name}has parameter{'s' if len(missed_params) > 1 else ''} {extra_params}, "
            f"but MPGLite provides only the following optional parameters: {provided_params}."
        )

    return kwargs


def smart_call(func: Callable | None, **available_data):
    """
    Calls func with only the arguments it actually asked for. It does nothing if func is None.
    Raises SignatureError if we don't pass a mandatory argument that the callback func expects.
    """

    if not func:
        return None

    return func(**smart_kwargs(func, **available_data))


@contextmanager
def open_error(filename: str, mode: str | None = "r"):
    """Attempts to open a file, and yields the file object and an error object if it fails. If the file is opened, it yields the file object and None. If the file fails to open, it yields None and the error object."""
    try:
        f = open(filename, mode)
    except IOError as err:
        yield None, err
    else:
        try:
            yield f, None
        finally:
            f.close()
