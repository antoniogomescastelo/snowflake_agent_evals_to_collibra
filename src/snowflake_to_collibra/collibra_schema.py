"""Names and ids of the Collibra asset types, relations and attributes the export relies on.
They must already exist in the target Collibra instance."""

# Asset types (public ids)
AI_AGENT_ASSET_TYPE = "AIAgent"
AI_AGENT_VERSION_ASSET_TYPE = "AIAgentVersion"
AI_ENDPOINT_ASSET_TYPE = "AIEndpoint"
AI_MONITOR_ASSET_TYPE = "AIMonitor"
AI_EVALUATION_RECORD_ASSET_TYPE = "AIMonitorEvaluations_C"

# Binary relation: agent -> version
AI_AGENT_HAS_VERSION_RELATION_TYPE = "PUBLIC_ID:AgentHasVersion:SOURCE"

# Complex relation: the agent deployment, and its legs
AI_AGENT_DEPLOYMENT_RELATION_TYPE = "00000000-0000-0000-0000-000000007505"
IS_DEPLOYMENT_OF_AI_AGENT_VERSION_LEG = "00000000-0000-0000-0000-000000007213:TARGET"
IS_EXPOSED_ON_AI_ENDPOINT_LEG = "00000000-0000-0000-0000-000000007214:TARGET"
IS_MONITORED_BY_AI_MONITOR_LEG = "00000000-0000-0000-0000-000000007215:TARGET"

COMPLEX_RELATION_EXTERNAL_SYSTEM_ID = "version"

# AI Agent Version attributes
VERSION_ATTRIBUTE = "Version"
LAST_EVALUATION_RUN_ATTRIBUTE = "LastAgentEvaluationRun_C"
LAST_EVALUATION_START_ATTRIBUTE = "LastAgentEvaluationStart_C"
LAST_EVALUATION_END_ATTRIBUTE = "LastAgentEvaluationEnd_C"
RECORDS_EVALUATED_ATTRIBUTE = "RecordsEvaluated_C"

# AI Monitor attributes
METRIC_TYPE_ATTRIBUTE = "MetricType_C"
RECORDS_SCORED_ATTRIBUTE = "RecordsScored_C"
AVERAGE_SCORE_ATTRIBUTE = "AverageScore_C"
ROWS_PASSED_ATTRIBUTE = "RowsPassed"
ROWS_FAILED_ATTRIBUTE = "RowsFailed"

# AI Monitor Evaluations (evaluation record) attributes
RECORD_INPUT_ATTRIBUTE = "Query_C"
RECORD_OUTPUT_ATTRIBUTE = "Answer_C"
RECORD_GROUND_TRUTH_ATTRIBUTE = "GroundTruth_C"
RECORD_AVERAGE_SCORE_ATTRIBUTE = "AverageScore_C"
RECORD_METRIC_NAME_ATTRIBUTE = "MetricName_C"
RECORD_CRITERIA_ATTRIBUTE = "Criteria_C"
RECORD_EXPLANATION_ATTRIBUTE = "Explanation_C"

# Binary relation: monitor -> record
AI_MONITOR_CONTAINS_EVALUATION_RELATION_TYPE = "PUBLIC_ID:AIMonitorContainsAIMonitorEvaluations_C:SOURCE"

# Agent deployment complex relation attributes
TRAFFIC_SPLIT_PERCENTAGE_ATTRIBUTE = "TrafficSplitPercentage"
