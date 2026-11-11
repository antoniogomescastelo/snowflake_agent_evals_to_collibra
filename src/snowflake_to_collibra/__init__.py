"""Export Snowflake Cortex Agent evaluation results to Collibra.

Reads the latest evaluation run of a Snowflake Agent, builds Collibra import
commands (AI Agent, Agent Version, Endpoint, Monitors and the deployment
complex relation), writes them to a JSON file and imports them into Collibra.
"""
