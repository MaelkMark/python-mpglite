from mpglite.utils import *
from mpglite.exceptions import SignatureError
import pytest


def test_format_list_with_and():
    assert format_list_with_and([]) == ""
    assert format_list_with_and([1]) == "1"
    assert format_list_with_and([1, 2]) == "1 and 2"
    assert format_list_with_and([1, 2, 3]) == "1, 2 and 3"
    assert format_list_with_and([1, 2, 3, 4]) == "1, 2, 3 and 4"


def test_smart_kwargs():
    assert smart_kwargs(None) == {}

    available_data = {"a": 1, "b": 2}

    assert smart_kwargs(lambda: None) == {}
    assert smart_kwargs(lambda a: None, **available_data) == {"a": 1}
    assert smart_kwargs(lambda **kwargs: None, **available_data) == available_data

    with pytest.raises(SignatureError):
        smart_kwargs(lambda x: None, **available_data)

    with pytest.raises(SignatureError):
        smart_kwargs(lambda a, b, c: None, **available_data)


def test_smart_call():
    assert smart_call(None) is None

    available_data = {"a": 1, "b": 2}

    assert smart_call(lambda a: a, **available_data) == 1
    assert smart_call(lambda a, b: a + b, **available_data) == 3
    assert smart_call(lambda **kwargs: kwargs, **available_data) == available_data

    with pytest.raises(SignatureError):
        smart_call(lambda c: c, **available_data)


def test_open_error(tmp_path):
    # Test successful open
    file_path = tmp_path / "test_file.txt"
    file_path.write_text("Hello World")

    with open_error(str(file_path), "r") as (f, err):
        assert err is None
        assert f is not None
        assert f.read() == "Hello World"

    assert f.closed

    # Test failed open
    with open_error(str(tmp_path / "non_existent.txt"), "r") as (f, err):
        assert f is None
        assert isinstance(err, IOError)
