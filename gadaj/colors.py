"""ANSI color utilities for terminal output."""


class _Colors:
    """Conditional ANSI color wrapper. No-op when disabled."""

    def __init__(self, enabled: bool, cost_warn_usd: float, cost_alert_usd: float):
        self.enabled = enabled
        self.cost_warn = cost_warn_usd
        self.cost_alert = cost_alert_usd

    def dim(self, text: str) -> str:
        """Label/fixed content → dim/grey."""
        return f"\x1b[2m{text}\x1b[0m" if self.enabled else text

    def duration(self, text: str) -> str:
        """Duration values → cyan."""
        return f"\x1b[36m{text}\x1b[0m" if self.enabled else text

    def cost(self, text: str, usd: float) -> str:
        """Cost values → dark-yellow / dark-orange / dark-red by threshold."""
        if not self.enabled:
            return text
        if usd >= self.cost_alert:
            return f"\x1b[31m{text}\x1b[0m"  # dark red
        if usd >= self.cost_warn:
            return f"\x1b[33m{text}\x1b[0m"  # dark orange (yellow ANSI)
        return f"\x1b[2;33m{text}\x1b[0m"     # dim yellow
