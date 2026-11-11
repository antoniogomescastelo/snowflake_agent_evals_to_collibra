"""The SQL queries run against Snowflake's AI Observability functions.
Each one uses `%s` placeholders; the parameter order is documented next to the query. `{agent}` below stands for the
four agent parameters (database, schema, agent name, agent type)."""

# Parameters: agent
LATEST_EVALUATION_RUN = """
SELECT
record_attributes:"snow.ai.observability.run.name"::string AS run_name,
record_attributes:"snow.ai.observability.object.version.name"::string AS agent_version,
COUNT(*) AS records_evaluated,
MIN(start_timestamp) as started_at,
MAX(timestamp) AS finished_at
FROM TABLE(SNOWFLAKE.LOCAL.GET_AI_OBSERVABILITY_EVENTS(%s, %s, %s, %s))
WHERE record_attributes:"ai.observability.span_type"::string = 'eval_root'
GROUP BY run_name, agent_version
ORDER BY finished_at DESC
LIMIT 1;
"""

# Parameters: pass threshold, fail threshold, agent, run name
METRIC_AGGREGATES = """
SELECT
record_attributes:"ai.observability.eval.metric_name"::string AS metric_name,
record_attributes:"ai.observability.eval.metric_type"::string AS metric_type,
SUM(record_attributes:"ai.observability.eval_root.n_calls"::float) AS records_scored,
ROUND(AVG(record_attributes:"ai.observability.eval_root.score"::float), 6) AS avg_score,
COUNT_IF(record_attributes:"ai.observability.eval_root.score"::float >= %s) AS pass_n,
COUNT_IF(record_attributes:"ai.observability.eval_root.score"::float <  %s) AS fail_n
FROM TABLE(SNOWFLAKE.LOCAL.GET_AI_OBSERVABILITY_EVENTS(%s, %s, %s, %s))
WHERE record_attributes:"ai.observability.span_type"::string = 'eval_root'
AND record_attributes:"snow.ai.observability.run.name"::string = %s
GROUP BY metric_name, metric_type;
"""

# Parameters: agent, agent, run name, run name
RUN_TOKEN_USAGE = """
SELECT
SUM(total_input_tokens) AS total_input_tokens,
SUM(total_output_tokens) AS total_output_tokens
FROM (
SELECT DISTINCT
B.record_id,
B.total_input_tokens,
B.total_output_tokens
FROM TABLE(SNOWFLAKE.LOCAL.GET_AI_OBSERVABILITY_EVENTS(%s, %s, %s, %s)) A,
TABLE (SNOWFLAKE.LOCAL.GET_AI_EVALUATION_DATA(%s, %s, %s, %s, %s)) B
WHERE A.record_attributes:"ai.observability.span_type"::string = 'eval_root'
AND A.record_attributes:"snow.ai.observability.run.name"::string = %s
AND B.record_id=A.record_attributes:"ai.observability.eval.target_record_id");
"""

# Parameters: agent, run name
EVALUATION_RECORDS = """
SELECT
B.input,
B.output,
B.ground_truth,
B.metric_name,
ROW_NUMBER() OVER (PARTITION BY B.metric_name ORDER BY B.record_id ) AS metric_number,
B.eval_agg_score,
B.metric_calls,
array_size(B.metric_calls) AS metric_calls_count
FROM TABLE(SNOWFLAKE.LOCAL.GET_AI_OBSERVABILITY_EVENTS(%s, %s, %s, %s)) A,
TABLE (SNOWFLAKE.LOCAL.GET_AI_EVALUATION_DATA(%s, %s, %s, %s, %s)) B
WHERE A.record_attributes:"ai.observability.span_type"::string = 'eval_root'
AND A.record_attributes:"snow.ai.observability.run.name"::string = %s
AND B.record_id=A.record_attributes:"ai.observability.eval.target_record_id"
AND B.metric_name=A.record_attributes:"ai.observability.eval.metric_name"
ORDER BY B.metric_name, B.record_id;
"""
