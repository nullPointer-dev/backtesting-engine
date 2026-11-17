from app.strategy_engine.validation import validate_strategy
from tests.helpers import cond, group, indicator, price, value

ENTRY = cond(price("close"), ">", value(10))
EXIT = cond(price("close"), "<", value(10))


def _strategy(**overrides):
    base = {"long_entry": ENTRY, "long_exit": EXIT}
    base.update(overrides)
    return base


def test_valid_strategy():
    result = validate_strategy(_strategy(
        long_entry=cond(indicator("SMA", period=20), "crosses_above", indicator("EMA", period=50)),
        short_entry=cond(indicator("BB_UPPER", period=20, std_dev=2.5), "<", price("close")),
        short_exit=EXIT,
    ))
    assert result.valid and result.errors == [] and result.definition is not None


def test_missing_required_rule():
    result = validate_strategy({"long_entry": ENTRY})
    assert not result.valid
    assert any(error.startswith("long_exit") for error in result.errors)


def test_malformed_operand():
    result = validate_strategy(_strategy(long_entry=cond({"type": "nope"}, ">", value(1))))
    assert not result.valid


def test_empty_group():
    result = validate_strategy(_strategy(long_entry=group("AND")))
    assert not result.valid
    assert "at least 1 item" in result.errors[0]


def test_unknown_indicator():
    result = validate_strategy(_strategy(long_entry=cond(indicator("SMAX"), ">", value(1))))
    assert len(result.errors) == 1
    assert result.errors[0].startswith("long_entry.left.indicator: unknown indicator 'SMAX'")


def test_parameter_checks():
    entry = group(
        "AND",
        cond(indicator("SMA", length=20), ">", value(1)),       # wrong name
        cond(indicator("SMA", period=20.5), ">", value(1)),     # not whole
        cond(indicator("SMA", period=0), ">", value(1)),        # below min
        cond(indicator("SMA", period="20"), ">", value(1)),     # not a number
        cond(indicator("SMA", period=True), ">", value(1)),     # bool is not a number
        cond(indicator("OBV", period=5), ">", value(1)),        # takes no params
    )
    result = validate_strategy(_strategy(long_entry=entry))
    messages = "\n".join(result.errors)
    assert len(result.errors) == 6
    assert "unknown parameter for SMA (allowed: period)" in messages
    assert "must be a whole number" in messages
    assert "must be at least 1" in messages
    assert messages.count("must be a number") == 2
    assert "unknown parameter for OBV (allowed: none)" in messages


def test_float_parameter_accepts_integer_value():
    result = validate_strategy(_strategy(long_entry=cond(indicator("BB_LOWER", std_dev=2), ">", value(1))))
    assert result.valid


def test_short_entry_requires_short_exit():
    result = validate_strategy(_strategy(short_entry=ENTRY))
    assert not result.valid
    assert result.errors[0].startswith("short_exit: required")


def test_short_exit_without_entry_is_a_warning():
    result = validate_strategy(_strategy(short_exit=EXIT))
    assert result.valid
    assert result.warnings == ["short_exit: ignored because there is no short_entry"]


def test_constant_comparison_warning():
    result = validate_strategy(_strategy(long_exit=cond(value(1), ">", value(2))))
    assert result.valid
    assert "compares two constant values" in result.warnings[0]


def test_macd_fast_slower_than_slow_warning():
    macd = indicator("MACD_LINE", fast_period=30, slow_period=10)
    result = validate_strategy(_strategy(long_entry=cond(macd, ">", value(0))))
    assert result.valid
    assert "fast_period should be smaller than slow_period" in result.warnings[0]
