"""Reads the evaluation data of a Snowflake agent."""

import json
import logging

import snowflake.connector

from . import snowflake_queries as queries
from .errors import ExportError
from .models import EvaluationMetric, EvaluationRecord, EvaluationResult, EvaluationRun, TokenUsage
from .timestamps import to_utc

logger = logging.getLogger(__name__)


def connect_to_snowflake(config):
    """Open and return a Snowflake connection using key-pair authentication from a SnowflakeConfig.
    Raises ExportError if the connection fails."""

    connection_parameters = {
        "account": config.account,
        "host": config.host,
        "port": config.port,
        "protocol": config.protocol,
        "user": config.user,
        "role": config.role,
        "warehouse": config.warehouse,
        "private_key_file": config.private_key_file,
    }

    try:
        conn = snowflake.connector.connect(
            **connection_parameters, enable_server_session_keep_alive_auto_detection=False
        )
    except snowflake.connector.errors.Error as e:
        raise ExportError(f"Unable to connect to Snowflake: {e}") from e

    logger.info("Connected to Snowflake account %s as %s", config.account, config.role)

    return conn


def parse_evaluation_run(row):
    """Build an EvaluationRun from a Snowflake dict row."""

    return EvaluationRun(
        run_name=row["RUN_NAME"],
        agent_version=row["AGENT_VERSION"],
        records_evaluated=int(row["RECORDS_EVALUATED"]),
        started_at=to_utc(row["STARTED_AT"]),
        finished_at=to_utc(row["FINISHED_AT"]),
    )


def parse_evaluation_metric(row):
    """Build an EvaluationMetric from a Snowflake dict row."""

    return EvaluationMetric(
        metric_name=row["METRIC_NAME"],
        metric_type=row["METRIC_TYPE"],
        records_scored=float(row["RECORDS_SCORED"]),
        avg_score=float(row["AVG_SCORE"]),
        pass_count=int(row["PASS_N"]),
        fail_count=int(row["FAIL_N"]),
    )


def parse_evaluation_record(row):
    """Build an EvaluationRecord from a Snowflake dict row. The metric calls are a VARIANT that the connector
    returns as a JSON string, so it is decoded here; a missing value counts as no calls. The ground truth and
    the aggregated score are optional."""

    metric_calls = row["METRIC_CALLS"]

    if isinstance(metric_calls, str):
        metric_calls = json.loads(metric_calls)

    score = row["EVAL_AGG_SCORE"]

    return EvaluationRecord(
        input=row["INPUT"],
        output=row["OUTPUT"],
        ground_truth=row["GROUND_TRUTH"],
        metric_name=row["METRIC_NAME"],
        metric_number=int(row["METRIC_NUMBER"]),
        eval_agg_score=None if score is None else float(score),
        metric_calls=metric_calls or [],
        metric_calls_count=int(row["METRIC_CALLS_COUNT"] or 0),
    )


def parse_token_usage(row):
    """Build a TokenUsage from a Snowflake dict row. The totals are SUMs, which are NULL when the run has no
    token data, so a missing total counts as 0."""

    return TokenUsage(
        input_tokens=int(row["TOTAL_INPUT_TOKENS"] or 0),
        output_tokens=int(row["TOTAL_OUTPUT_TOKENS"] or 0),
    )


class SnowflakeEvaluationReader:
    """Reads the evaluation data of one Snowflake agent through the AI observability functions.
    Owns the connection and the agent parameters that every query needs."""

    def __init__(self, conn, agent_name, agent_type):
        self.conn = conn
        self.agent_name = agent_name
        self.agent_type = agent_type.upper()
        self.agent_params = agent_name.snowflake_params(agent_type)

    def _query(self, sql, params, fetch_one=False):
        """Run `sql` and return the first dict row (or None) if `fetch_one`, otherwise all the dict rows."""

        with self.conn.cursor(snowflake.connector.DictCursor) as cur:
            cur.execute(sql, params)

            return cur.fetchone() if fetch_one else cur.fetchall()

    def query_latest_evaluation_run(self):
        """Return the most recent evaluation run of the agent as a dict row, or None if it has no runs.
        The row holds the run name, agent version, number of records evaluated and the start/finish timestamps."""

        return self._query(queries.LATEST_EVALUATION_RUN, self.agent_params, fetch_one=True)

    def query_metric_aggregates(self, run_name, pass_threshold, fail_threshold):
        """Return per-metric aggregates (records scored, average score, pass/fail counts) for `run_name`."""

        params = (pass_threshold, fail_threshold, *self.agent_params, run_name)

        return self._query(queries.METRIC_AGGREGATES, params)

    def query_latest_evaluation_run_tokens(self, run_name):
        """Return the total input and output tokens used by the records of `run_name` as a dict row."""

        params = (*self.agent_params, *self.agent_params, run_name, run_name)

        return self._query(queries.RUN_TOKEN_USAGE, params, fetch_one=True)

    def query_evaluation_records(self, run_name):
        """Return the record-level evaluation data for `run_name`, newest first."""

        params = (*self.agent_params, *self.agent_params, run_name, run_name)

        return self._query(queries.EVALUATION_RECORDS, params)

    def fetch_latest_evaluation(self, pass_threshold, fail_threshold):
        """Fetch the latest evaluation run from Snowflake and return it as an EvaluationResult.
        Raises ExportError if the queries fail or no runs exist."""

        try:
            latest_run = self.query_latest_evaluation_run()

            if latest_run is None:
                raise ExportError(f"No evaluation runs found for agent {self.agent_name}")

            run = parse_evaluation_run(latest_run)

            logger.info(
                "Found evaluation run %s for agent %s (version=%s)",
                run.run_name, self.agent_name, run.agent_version
            )

            metrics = [
                parse_evaluation_metric(row)
                for row in self.query_metric_aggregates(run.run_name, pass_threshold, fail_threshold)
            ]

            logger.info(
                "Found %d metric aggregates for agent %s (version=%s)",
                len(metrics), self.agent_name, run.agent_version
            )

            tokens = parse_token_usage(self.query_latest_evaluation_run_tokens(run.run_name))

            logger.info(
                "Found %d token usage for agent %s (version=%s)",
                tokens.input_tokens + tokens.output_tokens, self.agent_name, run.agent_version
            )

            records = [parse_evaluation_record(row) for row in self.query_evaluation_records(run.run_name)]

            logger.info(
                "Found %d evaluation records for agent %s (version=%s)",
                len(records), self.agent_name, run.agent_version
            )

        except snowflake.connector.errors.Error as e:
            raise ExportError(f"Unable to fetch Snowflake evaluation data: {e}") from e

        return EvaluationResult(run=run, metrics=metrics, tokens=tokens, records=records)
