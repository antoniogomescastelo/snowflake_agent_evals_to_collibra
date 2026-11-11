"""Collibra REST API client."""

import logging
import os
import time

import requests

from .errors import CollibraError

logger = logging.getLogger(__name__)


TERMINAL_JOB_STATES = {"COMPLETED", "CANCELED", "ERROR"}

REQUEST_TIMEOUT_SECONDS = 30

DEFAULT_IMPORT_TIMEOUT_SECONDS = 300


def describe_failure(error):
    """Describe a failed request: Collibra's own message when the error response carries one, else the error."""

    response = getattr(error, "response", None)

    if response is not None:
        try:
            body = response.json()
        except ValueError:
            body = None

        if isinstance(body, dict) and body.get("userMessage"):
            return f"HTTP {response.status_code}: {body['userMessage']}"

    return str(error)


class CollibraClient:
    """Thin wrapper around the Collibra REST APIs, bound to one instance and one target domain.
    Holds the credentials and reuses a single HTTP session for all requests.
    Every method raises CollibraError if the request fails, Collibra answers with an error status, or the
    response can't be parsed."""

    def __init__(self, base_url, username, password, domain_id):
        self.base_url = base_url
        self.username = username
        self.domain_id = domain_id
        self.session = requests.Session()
        self.session.auth = (username, password)

    @classmethod
    def from_config(cls, config):
        """Build a client from a CollibraConfig."""

        return cls(config.url, config.username, config.password, config.domain_id)

    def _request(self, method, path, description, **kwargs):
        """Send a request to `path` and return the response. Raises CollibraError, mentioning `description`, if it
        can't be sent or Collibra answers with an error status."""

        try:
            response = self.session.request(
                method, f"{self.base_url}{path}", timeout=REQUEST_TIMEOUT_SECONDS, **kwargs
            )

            response.raise_for_status()
        except requests.RequestException as e:
            raise CollibraError(f"Unable to {description}: {describe_failure(e)}") from e

        return response

    def _request_json(self, method, path, description, **kwargs):
        """Like `_request`, but return the parsed JSON body. Raises CollibraError if the body is not JSON."""

        response = self._request(method, path, description, **kwargs)

        try:
            return response.json()
        except ValueError as e:
            raise CollibraError(f"Unable to {description}: the response is not valid JSON") from e

    def fetch_domain(self):
        """Fetch the target Collibra domain by UUID and return the parsed JSON response."""

        return self._request_json("GET", f"/rest/2.0/domains/{self.domain_id}", f"fetch domain {self.domain_id}")

    def check_domain_access(self):
        """Check that Collibra is reachable with the configured credentials and that the target domain exists.
        Logs the connection and the domain found, and returns the domain. Raises CollibraError if it fails."""

        domain = self.fetch_domain()

        logger.info("Connected to Collibra instance %s as %s", self.base_url, self.username)

        logger.info("Found domain %s (%s), update", domain.get('name'), domain.get('id'))

        return domain

    def search_assets(self, asset_name, asset_type):
        """Search the target domain for assets with an exact name and type; return the parsed JSON response."""

        return self._request_json(
            "GET",
            "/rest/2.0/assets",
            f"search for asset {asset_name}",
            params={
                "name": asset_name,
                "nameMatchMode": "EXACT",
                "typePublicIds": asset_type,
                "domainId": self.domain_id,
            },
        )

    def run_import_job(self, import_file, poll_interval_seconds=1, max_wait_seconds=DEFAULT_IMPORT_TIMEOUT_SECONDS):
        """Upload `import_file` to the Collibra JSON import API, wait for the job to finish and return the final
        job dict. Polls every `poll_interval_seconds`.
        Raises CollibraError if the upload or polling fails, the job is not in a terminal state within
        `max_wait_seconds`, or it does not finish with the result SUCCESS."""

        file_name = os.path.basename(import_file)

        logger.info("Uploading the %s commands file to Collibra", import_file)

        with open(import_file, "rb") as file:
            job = self._request_json(
                "POST",
                "/rest/2.0/import/json-job",
                "start the import job",
                files={"file": (file_name, file, "application/json")},
                data={"fileName": file_name, "continueOnError": "false"},
            )

        deadline = time.monotonic() + max_wait_seconds

        logger.info("Import job %s started (state=%s)", job.get("id"), job.get("state"))

        while job.get("state") not in TERMINAL_JOB_STATES:
            if time.monotonic() > deadline:
                raise CollibraError(f"Import job {job.get('id')} did not finish within {max_wait_seconds}s")

            time.sleep(poll_interval_seconds)

            job = self._request_json("GET", f"/rest/2.0/jobs/{job['id']}", f"poll import job {job['id']}")

            logger.debug("Import job %s state: %s", job.get("id"), job.get("state"))

        logger.info(
            "Import job %s finished (state=%s, result=%s)", job.get("id"), job.get("state"), job.get("result")
        )

        if job.get("result") != "SUCCESS":
            raise CollibraError(f"Collibra import finished with result {job.get('result')}: {job}")

        return job

    def update_metrics(self, metrics):
        """Submit a batch of metrics to the Collibra AI Governance metrics API.
        `metrics` is a list of metric dicts (correlationId, assetId, date, data). Any 2xx status counts as success
        (the API answers 202 Accepted); the response body is not used."""

        self._request(
            "POST", "/rest/aiGovernance/v1/metrics/batch", "update the metrics", json={"metrics": metrics}
        )
