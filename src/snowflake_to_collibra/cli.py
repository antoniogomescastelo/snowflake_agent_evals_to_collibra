"""Command-line interface: parses the arguments, configures logging and runs the export."""

import argparse
import logging
import sys

from .collibra_client import DEFAULT_IMPORT_TIMEOUT_SECONDS
from .errors import ExportError
from .export import ExportOptions, run_export
from .models import AgentName

logger = logging.getLogger(__name__)


def agent_name_argument(value):
    """argparse type for `--agent-name`: parse DATABASE.SCHEMA.AGENT into an AgentName."""

    try:
        return AgentName.parse(value)
    except ValueError as e:
        raise argparse.ArgumentTypeError(str(e)) from e


def parse_args():
    """Parse and return the command-line arguments."""

    parser = argparse.ArgumentParser(
        prog="snowflake-to-collibra",
        description="Export Snowflake Agent evaluation results to Collibra"
    )

    parser.add_argument(
        "--agent-name",
        required=True,
        type=agent_name_argument,
        help="Snowflake Agent qualified name (DATABASE.SCHEMA.AGENT)",
    )

    parser.add_argument(
        "--agent-type",
        default="CORTEX AGENT",
        help="Snowflake Agent type"
    )

    parser.add_argument(
        "--pass-evaluation-if",
        type=float,
        default=0.5,
        help="Pass if the score is greater than or equal to this value (default: %(default)s)"
    )

    parser.add_argument(
        "--fail-evaluation-if",
        type=float,
        default=0.5,
        help="Fail if the score is smaller than this value (default: %(default)s)"
    )

    parser.add_argument(
        "--output",
        default="import_agents.json",
        help="The Collibra import output file"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build and write the import file, but skip the Collibra import and the metrics update",
    )

    parser.add_argument(
        "--env-file",
        default=".env",
        help="File to read the configuration from; environment variables override it (default: %(default)s)",
    )

    parser.add_argument(
        "--import-timeout",
        type=int,
        default=DEFAULT_IMPORT_TIMEOUT_SECONDS,
        help="Seconds to wait for the Collibra import job to finish (default: %(default)s)",
    )

    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        type=str.upper,
        help="Logging verbosity",
    )

    return parser.parse_args()


def main():
    """Parse the arguments, configure logging and run the export. Exits with status 1 if the export fails."""

    args = parse_args()

    logging.basicConfig(level=args.log_level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    # keep third-party libraries quieter unless debugging
    if args.log_level != "DEBUG":
        logging.getLogger("snowflake").setLevel(logging.ERROR)
        logging.getLogger("urllib3").setLevel(logging.ERROR)

    try:
        run_export(
            ExportOptions(
                agent_name=args.agent_name,
                agent_type=args.agent_type,
                pass_evaluation_if=args.pass_evaluation_if,
                fail_evaluation_if=args.fail_evaluation_if,
                output=args.output,
                dry_run=args.dry_run,
                env_file=args.env_file,
                import_timeout=args.import_timeout,
            )
        )
    except ExportError as e:
        logger.error("%s", e)
        sys.exit(1)
