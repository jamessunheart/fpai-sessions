"""
Message templates for common notification types
"""
from typing import Dict, Any


class MessageTemplates:
    """Predefined message templates"""

    TEMPLATES: Dict[str, str] = {
        "trade_alert": "🚨 Trade Alert: {symbol} {side} at ${price}",
        "position_closed": "✅ Position Closed: {symbol} P&L: {pnl}",
        "droplet_restart": "🔄 Droplet Restarted: {name} - {reason}",
        "error_alert": "❌ Error in {service}: {error}",
        "daily_summary": "📊 Daily Summary:\n- Trades: {trades}\n- P&L: {pnl}",
        "system_status": "🔵 System Status: {status}\n{details}",
        "health_warning": "⚠️ Health Warning: {service}\n{issue}",
        "deployment_success": "🚀 Deployment Successful: {service} v{version}",
        "deployment_failed": "🔴 Deployment Failed: {service}\n{error}",
        "budget_alert": "💰 Budget Alert: {category} - {amount} spent ({percentage}%)",
    }

    @classmethod
    def render(cls, template_name: str, data: Dict[str, Any]) -> str:
        """
        Render a template with provided data

        Args:
            template_name: Name of the template
            data: Dictionary of template variables

        Returns:
            Rendered message string

        Raises:
            ValueError: If template not found
        """
        if template_name not in cls.TEMPLATES:
            available = ", ".join(cls.TEMPLATES.keys())
            raise ValueError(
                f"Template '{template_name}' not found. "
                f"Available templates: {available}"
            )

        template = cls.TEMPLATES[template_name]
        try:
            return template.format(**data)
        except KeyError as e:
            raise ValueError(
                f"Missing required template variable: {e}. "
                f"Template: {template_name}"
            )

    @classmethod
    def list_templates(cls) -> Dict[str, str]:
        """Get all available templates"""
        return cls.TEMPLATES.copy()

    @classmethod
    def add_template(cls, name: str, template: str) -> None:
        """Add a new template dynamically"""
        cls.TEMPLATES[name] = template

    @classmethod
    def get_template(cls, name: str) -> str:
        """Get a template by name"""
        return cls.TEMPLATES.get(name, "")
