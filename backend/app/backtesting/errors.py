import re

_EXCEPTION_LINE = re.compile(r"^(?:[\w.]+\.)?(\w+(?:Error|Exception|Exit|Cancelled)): ?(.*)$")


def summarize_error(message: str | None) -> str | None:
    """One readable line from a stored error message.

    Tracebacks end with ``SomeError: what went wrong``; return just the part a
    person needs ("what went wrong"), or the exception name if it has no text.
    Messages that are already one line (e.g. "Cancelled by user") pass through.
    """
    if not message:
        return None
    lines = [line.strip() for line in message.strip().splitlines() if line.strip()]
    if not lines:
        return None
    last = lines[-1]
    match = _EXCEPTION_LINE.match(last)
    if match:
        return match.group(2).strip() or match.group(1)
    return last
