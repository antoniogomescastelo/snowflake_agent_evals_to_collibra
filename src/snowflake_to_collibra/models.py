"""Snowflake-side data classes: the agent and the evaluation data read from it."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class AgentName:
    """The qualified name of a Snowflake agent: DATABASE.SCHEMA.AGENT, normalized to upper case without spaces."""

    database: str
    schema: str
    name: str

    @classmethod
    def parse(cls, value):
        """Parse `DATABASE.SCHEMA.AGENT`. Raises ValueError if it doesn't have exactly three non-empty parts."""

        parts = value.upper().replace(" ", "").split(".")

        if len(parts) != 3 or not all(parts):
            raise ValueError(f"invalid agent name '{value}', expected format is DATABASE.SCHEMA.AGENT")

        return cls(*parts)

    def snowflake_params(self, agent_type):
        """Return (database, schema, agent, agent_type) as expected by the Snowflake observability functions."""

        return self.database, self.schema, self.name, agent_type.upper()

    def collibra_qualified_name(self, snowflake_account):
        """Return the Collibra name prefix of the agent: `ACCOUNT>DATABASE>SCHEMA>AGENT`."""

        return f"{snowflake_account}>{self.database}>{self.schema}>{self.name}"

    def __str__(self):
        return f"{self.database}.{self.schema}.{self.name}"


@dataclass(frozen=True)
class EvaluationRun:
    """The latest evaluation run of an agent."""

    run_name: str
    agent_version: str
    records_evaluated: int
    started_at: datetime
    finished_at: datetime


@dataclass(frozen=True)
class EvaluationMetric:
    """Aggregated scores of one evaluation metric in a run."""

    metric_name: str
    metric_type: str
    records_scored: float
    avg_score: float
    pass_count: int
    fail_count: int


@dataclass(frozen=True)
class EvaluationRecord:
    """The score of one evaluation metric on one record of a run."""

    input: str
    output: str
    ground_truth: str | None
    metric_name: str
    metric_number: int
    eval_agg_score: float | None
    metric_calls: list
    metric_calls_count: int


@dataclass(frozen=True)
class TokenUsage:
    """Total token usage of an evaluation run."""

    input_tokens: int
    output_tokens: int


@dataclass(frozen=True)
class EvaluationResult:
    """Everything fetched from Snowflake for the latest evaluation run. """

    run: EvaluationRun
    metrics: list[EvaluationMetric]
    tokens: TokenUsage
    records: list[EvaluationRecord]
