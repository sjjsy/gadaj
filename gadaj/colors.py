"""ANSI color utilities for terminal output."""

import re


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

    def nums(self, text: str) -> str:
        """Numeric values → dark blue."""
        return f"\x1b[34m{text}\x1b[0m" if self.enabled else text

    def colorize_digits(self, text: str) -> str:
        """Color bare digit sequences blue, skipping digits inside existing ANSI color blocks."""
        if not self.enabled:
            return text
        # Split by ANSI codes, track if we're inside a color block
        parts = re.split(r"(\x1b\[[0-9;]*m)", text)
        result = []
        inside_color = False
        for part in parts:
            if part.startswith("\x1b"):
                inside_color = part != "\x1b[0m"
                result.append(part)
            elif inside_color:
                result.append(part)  # inside colored block, don't re-color
            else:
                result.append(re.sub(r"\d+", lambda m: f"\x1b[34m{m.group()}\x1b[0m", part))
        return "".join(result)

    def cost(self, text: str, usd: float) -> str:
        """Cost values → dim-yellow / dark-amber / dark-red by threshold."""
        if not self.enabled:
            return text
        if usd >= self.cost_alert:
            return f"\x1b[31m{text}\x1b[0m"  # dark red
        if usd >= self.cost_warn:
            return f"\x1b[38;5;136m{text}\x1b[0m"  # dark golden amber (256-color)
        return f"\x1b[2;33m{text}\x1b[0m"     # dim yellow
