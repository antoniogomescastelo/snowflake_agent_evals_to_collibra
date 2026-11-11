"""Builds and submits the Collibra AI Governance metrics (pass/fail monitors and token usage)."""

import logging

from .errors import CollibraError
from .timestamps import format_timestamp

logger = logging.getLogger(__name__)


def build_monitor_metrics(run, monitors, version_id):
    """Build the PASS_FAIL_MONITOR metric payloads, one per MonitorAsset."""

    date = format_timestamp(run.finished_at, "%Y-%m-%d")

    return [
        {
            "correlationId": monitor.asset.id,
            "assetId": version_id,
            "date": date,
            "data": {
                "type": "PASS_FAIL_MONITOR",
                "monitorAssetId": monitor.asset.id,
                "passCount": monitor.metric.pass_count,
                "failCount": monitor.metric.fail_count,
                "errorCount": 0,
            },
        }
        for monitor in monitors
    ]


def build_token_metrics(run, tokens, version_id):
    """Build the TOKENS metric payload (as a one-item list) for the agent version."""

    return [
        {
            "correlationId": version_id,
            "assetId": version_id,
            "date": format_timestamp(run.finished_at, "%Y-%m-%d"),
            "data": {
                "type": "TOKENS",
                "inputCount": tokens.input_tokens,
                "outputCount": tokens.output_tokens,
            },
        }
    ]


def submit_metrics(client, label, metrics):
    """Submit `metrics` to Collibra. A failure is logged as a warning and does not fail the export.
    `label` names the kind of metrics (e.g. "monitor", "token") in log messages.
    Returns True if the metrics were submitted, False otherwise."""

    try:
        client.update_metrics(metrics)
    except CollibraError as e:
        logger.warning("Failed to upload the %s: %s", label, e)
        return False

    logger.info("Uploaded %d %s", len(metrics), label)

    return True
