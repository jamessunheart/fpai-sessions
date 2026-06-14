"""
Tests for message templates
"""
import pytest
from app.templates import MessageTemplates


def test_render_trade_alert():
    """Test rendering trade alert template"""
    result = MessageTemplates.render(
        "trade_alert",
        {"symbol": "BTC/USD", "side": "BUY", "price": "50000"}
    )
    assert "BTC/USD" in result
    assert "BUY" in result
    assert "50000" in result


def test_render_error_alert():
    """Test rendering error alert template"""
    result = MessageTemplates.render(
        "error_alert",
        {"service": "test-service", "error": "Connection timeout"}
    )
    assert "test-service" in result
    assert "Connection timeout" in result


def test_render_invalid_template():
    """Test rendering non-existent template"""
    with pytest.raises(ValueError, match="Template .* not found"):
        MessageTemplates.render("nonexistent", {})


def test_render_missing_variable():
    """Test rendering template with missing variable"""
    with pytest.raises(ValueError, match="Missing required template variable"):
        MessageTemplates.render("trade_alert", {"symbol": "BTC"})


def test_list_templates():
    """Test listing all templates"""
    templates = MessageTemplates.list_templates()
    assert isinstance(templates, dict)
    assert len(templates) > 0
    assert "trade_alert" in templates
    assert "error_alert" in templates


def test_add_template():
    """Test adding a custom template"""
    MessageTemplates.add_template("test_template", "Test: {value}")
    result = MessageTemplates.render("test_template", {"value": "123"})
    assert result == "Test: 123"


def test_get_template():
    """Test getting a specific template"""
    template = MessageTemplates.get_template("trade_alert")
    assert template
    assert "{symbol}" in template
