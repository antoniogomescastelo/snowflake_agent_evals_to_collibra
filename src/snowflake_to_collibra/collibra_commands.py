"""Builds the Collibra import commands. Pure: no I/O."""


from .collibra_models import ImportPlan
from .collibra_schema import (
    AI_AGENT_ASSET_TYPE,
    AI_AGENT_DEPLOYMENT_RELATION_TYPE,
    AI_AGENT_HAS_VERSION_RELATION_TYPE,
    AI_AGENT_VERSION_ASSET_TYPE,
    AI_ENDPOINT_ASSET_TYPE,
    AI_EVALUATION_RECORD_ASSET_TYPE,
    AI_MONITOR_ASSET_TYPE,
    AI_MONITOR_CONTAINS_EVALUATION_RELATION_TYPE,
    AVERAGE_SCORE_ATTRIBUTE,
    COMPLEX_RELATION_EXTERNAL_SYSTEM_ID,
    IS_DEPLOYMENT_OF_AI_AGENT_VERSION_LEG,
    IS_EXPOSED_ON_AI_ENDPOINT_LEG,
    IS_MONITORED_BY_AI_MONITOR_LEG,
    LAST_EVALUATION_END_ATTRIBUTE,
    LAST_EVALUATION_RUN_ATTRIBUTE,
    LAST_EVALUATION_START_ATTRIBUTE,
    METRIC_TYPE_ATTRIBUTE,
    RECORD_AVERAGE_SCORE_ATTRIBUTE,
    RECORD_CRITERIA_ATTRIBUTE,
    RECORD_EXPLANATION_ATTRIBUTE,
    RECORD_GROUND_TRUTH_ATTRIBUTE,
    RECORD_INPUT_ATTRIBUTE,
    RECORD_METRIC_NAME_ATTRIBUTE,
    RECORD_OUTPUT_ATTRIBUTE,
    RECORDS_EVALUATED_ATTRIBUTE,
    RECORDS_SCORED_ATTRIBUTE,
    ROWS_FAILED_ATTRIBUTE,
    ROWS_PASSED_ATTRIBUTE,
    TRAFFIC_SPLIT_PERCENTAGE_ATTRIBUTE,
    VERSION_ATTRIBUTE,
)
from .timestamps import format_timestamp


def drop_empty_attributes(attributes):
    """Remove attribute values that are None and attributes left without any value.
    Falsy but valid values such as 0 are kept."""

    cleaned = {
        name: [value for value in values if value.get("value") is not None]
        for name, values in attributes.items()
    }

    return {name: values for name, values in cleaned.items() if values}


def build_asset_command(
    asset_id, asset_name, asset_display_name, asset_type, domain_id, relations=None, attributes=None
):
    """Build a Collibra import command that creates or updates an Asset.
    `relations` and `attributes` are optional and only included when provided. Attributes without a value
    (None, or an empty list of values) are omitted."""

    command = {
        "resourceType": "Asset",
        "identifier": {"id": asset_id},
        "name": asset_name,
        "displayName": asset_display_name,
        "type": {"publicId": asset_type},
        "domain": {"id": domain_id},
    }

    if relations:
        command["relations"] = relations

    attributes = drop_empty_attributes(attributes or {})

    if attributes:
        command["attributes"] = attributes

    return command


def build_complex_relation_command(external_entity_id, relation_type, legs=None, attributes=None):
    """Build a Collibra import command that creates or updates a Complex Relation.
    `external_entity_id` identifies the relation across imports, so re-imports update the same relation.
    `legs` maps relation legs to target assets; `attributes` are optional."""

    command = {
        "resourceType": "Complex Relation",
        "identifier": {
            "externalSystemId": COMPLEX_RELATION_EXTERNAL_SYSTEM_ID,
            "externalEntityId": external_entity_id,
        },
        "complexRelationType": {"id": relation_type},
    }

    if legs:
        command["relations"] = legs

    if attributes:
        command["attributes"] = attributes

    return command


def build_agent_command(domain_id, agent):
    """Build the import command for the AI Agent."""

    return build_asset_command(agent.id, agent.name, agent.display_name, AI_AGENT_ASSET_TYPE, domain_id)


def build_agent_version_command(domain_id, version, agent, run):
    """Build the import command for the AI Agent Version, linked to its agent and carrying the latest run details."""

    return build_asset_command(
        version.id,
        version.name,
        version.display_name,
        AI_AGENT_VERSION_ASSET_TYPE,
        domain_id,
        relations={AI_AGENT_HAS_VERSION_RELATION_TYPE: [{"id": agent.id}]},
        attributes={
            VERSION_ATTRIBUTE: [{"value": run.agent_version}],
            LAST_EVALUATION_RUN_ATTRIBUTE: [{"value": run.run_name}],
            LAST_EVALUATION_START_ATTRIBUTE: [{"value": format_timestamp(run.started_at)}],
            LAST_EVALUATION_END_ATTRIBUTE: [{"value": format_timestamp(run.finished_at)}],
            RECORDS_EVALUATED_ATTRIBUTE: [{"value": run.records_evaluated}]
        }
    )


def build_endpoint_command(domain_id, endpoint):
    """Build the import command for the AI Endpoint."""

    return build_asset_command(
        endpoint.id, endpoint.name, endpoint.display_name, AI_ENDPOINT_ASSET_TYPE, domain_id
    )


def build_monitor_command(domain_id, monitor):
    """Build the import command for an AI Monitor (a MonitorAsset) from the metric it monitors."""

    return build_asset_command(
        monitor.asset.id,
        monitor.asset.name,
        monitor.asset.display_name,
        AI_MONITOR_ASSET_TYPE,
        domain_id,
        attributes={
            METRIC_TYPE_ATTRIBUTE: [{"value": monitor.metric.metric_type}],
            RECORDS_SCORED_ATTRIBUTE: [{"value": monitor.metric.records_scored}],
            AVERAGE_SCORE_ATTRIBUTE: [{"value": monitor.metric.avg_score}],
            ROWS_PASSED_ATTRIBUTE: [{"value": monitor.metric.pass_count}],
            ROWS_FAILED_ATTRIBUTE: [{"value": monitor.metric.fail_count}]
        }
    )


def build_record_command(domain_id, record_asset):
    """Build the import command for an AI Monitor Evaluations asset from one evaluation record.
    Attributes without a value (e.g. a missing ground truth or score) are omitted."""

    record = record_asset.record

    monitor_name = f"{'>'.join(record_asset.asset.name.split(">")[:-1])}[{AI_MONITOR_ASSET_TYPE}]"

    return build_asset_command(
        record_asset.asset.id,
        record_asset.asset.name,
        record_asset.asset.display_name,
        AI_EVALUATION_RECORD_ASSET_TYPE,
        domain_id,
        relations={AI_MONITOR_CONTAINS_EVALUATION_RELATION_TYPE: [{
            "name": monitor_name,
            "type": {"publicId": AI_MONITOR_ASSET_TYPE},
            "domain": {"id": domain_id}
        }]},
        attributes={
            RECORD_INPUT_ATTRIBUTE: [{"value": record.input}],
            RECORD_OUTPUT_ATTRIBUTE: [{"value": record.output}],
            RECORD_GROUND_TRUTH_ATTRIBUTE: [{"value": record.ground_truth}],
            RECORD_METRIC_NAME_ATTRIBUTE: [{"value": record.metric_name}],
            RECORD_AVERAGE_SCORE_ATTRIBUTE: [{"value": record.eval_agg_score}],
            RECORD_CRITERIA_ATTRIBUTE: [
                {"value": row["criteria"]} for row in record.metric_calls if "criteria" in row
            ],
            RECORD_EXPLANATION_ATTRIBUTE: [
                {"value": row["explanation"]} for row in record.metric_calls if "explanation" in row
            ],
        }
    )


def build_import_commands(domain_id, assets, evaluation):
    """Build the full list of Collibra import commands for an EvaluationResult and its ResolvedAssets: the agent,
    agent version, endpoint, one monitor per metric, one evaluation asset per record, and the deployment complex
    relation linking them. Returns an ImportPlan."""

    deployment_command = build_complex_relation_command(
        assets.version.name,
        AI_AGENT_DEPLOYMENT_RELATION_TYPE,
        legs={
            IS_DEPLOYMENT_OF_AI_AGENT_VERSION_LEG: [{"id": assets.version.id}],
            IS_EXPOSED_ON_AI_ENDPOINT_LEG: [{"id": assets.endpoint.id}],
            IS_MONITORED_BY_AI_MONITOR_LEG: [{"id": monitor.asset.id} for monitor in assets.monitors],
        },
        attributes={TRAFFIC_SPLIT_PERCENTAGE_ATTRIBUTE: [{"value": 100}]},
    )

    commands = [
        build_agent_command(domain_id, assets.agent),
        build_agent_version_command(domain_id, assets.version, assets.agent, evaluation.run),
        build_endpoint_command(domain_id, assets.endpoint),
        *(build_monitor_command(domain_id, monitor) for monitor in assets.monitors),
        deployment_command,
        *(build_record_command(domain_id, record) for record in assets.records)
    ]

    return ImportPlan(version_id=assets.version.id, commands=commands)
