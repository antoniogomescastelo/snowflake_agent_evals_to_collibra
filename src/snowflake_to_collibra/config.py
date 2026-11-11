"""Configuration loaded from the environment and the .env file."""

import logging
import os
from dataclasses import MISSING, dataclass, field, fields

from dotenv import dotenv_values

from .errors import ConfigError

logger = logging.getLogger(__name__)


def env_field(env_name, normalize=None, **kwargs):
    """A dataclass field loaded from the environment variable `env_name`. The `.env` file and the environment are
    the sources of its value, `normalize` optionally cleans up the (already stripped) string, and `default` makes
    it optional. A field without a default is required."""

    return field(metadata={"env": env_name, "normalize": normalize}, **kwargs)


@dataclass(frozen=True)
class SnowflakeConfig:
    """Connection settings for Snowflake (key-pair authentication)."""

    account: str = env_field("SNOWFLAKE_ACCOUNT")
    host: str = env_field("SNOWFLAKE_HOST")
    user: str = env_field("SNOWFLAKE_USER")
    role: str = env_field("SNOWFLAKE_ROLE")
    warehouse: str = env_field("SNOWFLAKE_WAREHOUSE")
    private_key_file: str = env_field("SNOWFLAKE_PRIVATE_KEY_FILE", normalize=os.path.expanduser)
    port: int = env_field("SNOWFLAKE_PORT", default=443)
    protocol: str = env_field("SNOWFLAKE_PROTOCOL", default="https")


@dataclass(frozen=True)
class CollibraConfig:
    """Connection settings for Collibra and the domain the assets are imported into."""

    url: str = env_field("COLLIBRA_URL", normalize=lambda value: value.rstrip("/"))
    username: str = env_field("COLLIBRA_USERNAME")
    password: str = env_field("COLLIBRA_PASSWORD", repr=False)
    domain_id: str = env_field("COLLIBRA_DOMAIN_UUID")


@dataclass(frozen=True)
class Config:
    """The validated configuration of the export."""

    snowflake: SnowflakeConfig
    collibra: CollibraConfig


def load_config(env_file=".env"):
    """Load the configuration and return it as a Config.
    Values come from the real environment first and then from `env_file`. They are stripped, and a variable that
    is set but empty counts as not set. Which variables exist, which are required and their defaults are declared
    on the config dataclasses.
    Raises ConfigError if a required variable is missing or a value is invalid."""

    if not os.path.isfile(env_file):
        logger.warning("Configuration file %s not found: using environment variables only", env_file)

    file_values = dotenv_values(env_file)

    def get(key):
        return (os.environ.get(key) or "").strip() or (file_values.get(key) or "").strip()

    missing = []
    invalid = []

    def collect(config_class):
        values = {}

        for config_field in fields(config_class):
            env_name = config_field.metadata["env"]
            raw_value = get(env_name)

            if not raw_value:
                if config_field.default is MISSING:
                    missing.append(env_name)
                else:
                    values[config_field.name] = config_field.default

                continue

            normalize = config_field.metadata["normalize"]
            value = normalize(raw_value) if normalize else raw_value

            if config_field.type is int:
                try:
                    value = int(value)
                except ValueError:
                    invalid.append(f"{env_name} must be a number, got '{raw_value}'")

                    continue

            values[config_field.name] = value

        return values

    snowflake_values = collect(SnowflakeConfig)
    collibra_values = collect(CollibraConfig)

    if missing:
        raise ConfigError(f"Missing configuration variables: {', '.join(missing)}")

    if invalid:
        raise ConfigError(f"Invalid configuration variables: {'; '.join(invalid)}")

    config = Config(snowflake=SnowflakeConfig(**snowflake_values), collibra=CollibraConfig(**collibra_values))

    if not os.path.isfile(config.snowflake.private_key_file):
        raise ConfigError(f"SNOWFLAKE_PRIVATE_KEY_FILE is not a file: {config.snowflake.private_key_file}")

    return config
