"""Timestamp helpers: Snowflake values are handled as UTC."""

from datetime import UTC


def to_utc(value):
    """Return a Snowflake timestamp as a UTC datetime. Timezone-aware values are converted, naive values are
    assumed to be UTC already (as for TIMESTAMP_NTZ columns of the event tables)."""

    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)

    return value.astimezone(UTC)


def format_timestamp(value, fmt="%Y-%m-%d %H:%M:%S"):
    """Format a UTC timestamp as a string."""

    return value.strftime(fmt)
