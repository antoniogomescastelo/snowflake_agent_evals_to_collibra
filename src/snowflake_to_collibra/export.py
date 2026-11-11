"""The export flow: Snowflake evaluation data in, Collibra assets and metrics out."""

import json
import logging
from dataclasses import dataclass

from .collibra_client import DEFAULT_IMPORT_TIMEOUT_SECONDS, CollibraClient
from .collibra_commands import build_import_commands
from .collibra_resolver import resolve_assets
from .config import load_config
from .metrics import build_monitor_metrics, build_token_metrics, submit_metrics
from .models import AgentName
from .snowflake_reader import SnowflakeEvaluationReader, connect_to_snowflake

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ExportOptions:
    """The options of one export run."""

    agent_name: AgentName
    agent_type: str = "CORTEX AGENT"
    pass_evaluation_if: float = 0.5
    fail_evaluation_if: float = 0.5
    output: str = "import_agents.json"
    dry_run: bool = False
    env_file: str = ".env"
    import_timeout: int = DEFAULT_IMPORT_TIMEOUT_SECONDS


def write_import_plan(plan, import_file):
    """Write the import commands of `plan` to `import_file` as JSON."""

    with open(import_file, "w") as file:
        json.dump(plan.commands, file, indent=2)

    logger.info("Wrote %d import commands to the %s file", len(plan.commands), import_file)


def run_export(options):
    """Run the export: fetch Snowflake evaluation data, write import commands and import them into Collibra.
    With `options.dry_run` the import file is written but nothing is imported or submitted.
    Raises ExportError on any failure that should stop the export."""

    logger.info("Starting export for agent %s", options.agent_name)

    config = load_config(options.env_file)

    with connect_to_snowflake(config.snowflake) as conn:
        reader = SnowflakeEvaluationReader(conn, options.agent_name, options.agent_type)

        evaluation = reader.fetch_latest_evaluation(options.pass_evaluation_if, options.fail_evaluation_if)

    client = CollibraClient.from_config(config.collibra)

    client.check_domain_access()

    assets = resolve_assets(client, options.agent_name, config.snowflake.account, evaluation)

    plan = build_import_commands(client.domain_id, assets, evaluation)

    write_import_plan(plan, options.output)

    if options.dry_run:
        logger.info("Dry run, skipping the Collibra import and the metrics update")

        return

    client.run_import_job(options.output, max_wait_seconds=options.import_timeout)

    monitor_metrics = build_monitor_metrics(evaluation.run, assets.monitors, plan.version_id)

    token_metrics = build_token_metrics(evaluation.run, evaluation.tokens, plan.version_id)

    results = {
        "monitor": submit_metrics(client, "metric aggregates", monitor_metrics),
        "token": submit_metrics(client, "token usage", token_metrics),
    }

    failed = [label for label, succeeded in results.items() if not succeeded]

    if failed:
        logger.warning("Export finished, but the %s metrics update may have failed", " and ".join(failed))


    logger.info("Done")
