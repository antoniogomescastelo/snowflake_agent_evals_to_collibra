"""Exceptions raised by the export."""

class ExportError(Exception):
    """A failure that stops the export. `main()` logs it and exits with a non-zero status."""


class ConfigError(ExportError):
    """The configuration is missing or invalid."""


class CollibraError(ExportError):
    """A request to Collibra failed: it could not be sent, Collibra answered with an error, or the answer was
    not what was expected."""
