from app.backtesting.errors import summarize_error

TRACEBACK = """Traceback (most recent call last):
  File "runner.py", line 80, in run
    raise ValueError(...)
ValueError: No market data for TCS.NS (1d) between 2020-01-01 and 2021-01-01
"""


def test_traceback_reduces_to_its_message():
    assert summarize_error(TRACEBACK) == "No market data for TCS.NS (1d) between 2020-01-01 and 2021-01-01"


def test_qualified_exception_names_and_bare_exceptions():
    assert summarize_error("Traceback\nsqlalchemy.exc.OperationalError: connection refused") == "connection refused"
    assert summarize_error("Traceback\nZeroDivisionError") == "ZeroDivisionError"


def test_plain_messages_pass_through():
    assert summarize_error("Cancelled by user") == "Cancelled by user"
    assert summarize_error(None) is None
    assert summarize_error("   \n") is None
