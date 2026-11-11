"""Resolves the identities of the Collibra assets of an export, creating new ids for assets that don't exist yet."""

import hashlib
import logging
import uuid

from .collibra_models import AssetIdentity, MonitorAsset, RecordAsset, ResolvedAssets
from .collibra_schema import (
    AI_AGENT_ASSET_TYPE,
    AI_AGENT_VERSION_ASSET_TYPE,
    AI_ENDPOINT_ASSET_TYPE,
    AI_EVALUATION_RECORD_ASSET_TYPE,
    AI_MONITOR_ASSET_TYPE,
)

logger = logging.getLogger(__name__)


def _input_digest(record_input):
    """Return a short stable digest of a record input, used to tell the records of a run and metric apart,
    since the records have no id of their own."""

    return hashlib.sha1(record_input.encode("utf-8")).hexdigest()[:12]


def resolve_asset(client, qualified_name, asset_type, default_display_name):
    """Look up the asset `qualified_name[asset_type]` in Collibra and return its AssetIdentity.
    An existing asset keeps its id and display name, a new one gets a new id and `default_display_name`.
    If several assets match, the first one is used and a warning is logged.
    Raises CollibraError if the search fails."""

    asset_name = f"{qualified_name}[{asset_type}]"

    response = client.search_assets(asset_name, asset_type)

    results = response.get("results", [])

    if not results:
        logger.info("Asset %s of type %s not found, create", asset_name, asset_type)

        return AssetIdentity(id=str(uuid.uuid4()), name=asset_name, display_name=default_display_name)

    logger.info("Asset %s of type %s found, update", asset_name, asset_type)

    asset = results[0]

    return AssetIdentity(id=asset["id"], name=asset_name, display_name=asset["displayName"])


def resolve_assets(client, agent_name, snowflake_account, evaluation):
    """Resolve the Collibra identities of the agent, agent version, endpoint and one monitor per metric.
    The asset names are derived from `agent_name` and `snowflake_account`.
    This is the only step of the command building that talks to Collibra."""

    agent_qualified_name = agent_name.collibra_qualified_name(snowflake_account)

    agent = resolve_asset(client, agent_qualified_name, AI_AGENT_ASSET_TYPE, agent_qualified_name)

    version = resolve_asset(
        client,
        f"{agent_qualified_name}>{evaluation.run.agent_version}",
        AI_AGENT_VERSION_ASSET_TYPE,
        f"{agent.display_name}>{evaluation.run.agent_version}",
    )

    endpoint = resolve_asset(client, agent_qualified_name, AI_ENDPOINT_ASSET_TYPE, agent.display_name)

    monitors = [
        MonitorAsset(
            asset=resolve_asset(
                client,
                f"{agent_qualified_name}>{metric.metric_name}",
                AI_MONITOR_ASSET_TYPE,
                f"{agent.display_name}>{metric.metric_name}",
            ),
            metric=metric,
        )
        for metric in evaluation.metrics
    ]

    records = [
        RecordAsset(
            asset=resolve_asset(
                client,
                f"{agent_qualified_name}>{record.metric_name}>{record.metric_number}",
                AI_EVALUATION_RECORD_ASSET_TYPE,
                f"{agent.display_name}>{record.metric_name}",
            ),
            record=record,
        )
        for record in evaluation.records
    ]

    return ResolvedAssets(agent=agent, version=version, endpoint=endpoint, monitors=monitors, records=records)
