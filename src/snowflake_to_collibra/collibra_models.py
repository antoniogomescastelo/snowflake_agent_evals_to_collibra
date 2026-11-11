"""Collibra-side data classes: asset identities and the import plan."""

from dataclasses import dataclass

from .models import EvaluationMetric, EvaluationRecord


@dataclass(frozen=True)
class AssetIdentity:
    """The identity of a Collibra asset: the id of the existing asset, or a new id if it doesn't exist yet."""

    id: str
    name: str
    display_name: str


@dataclass(frozen=True)
class MonitorAsset:
    """The Collibra identity of an AI Monitor, together with the metric it monitors."""

    asset: AssetIdentity
    metric: EvaluationMetric


@dataclass(frozen=True)
class RecordAsset:
    """The Collibra identity of an evaluation record, together with the record it represents."""

    asset: AssetIdentity
    record: EvaluationRecord


@dataclass(frozen=True)
class ResolvedAssets:
    """The Collibra identities of all the assets of an export, with one monitor per evaluation metric and one
    asset per evaluation record."""

    agent: AssetIdentity
    version: AssetIdentity
    endpoint: AssetIdentity
    monitors: list[MonitorAsset]
    records: list[RecordAsset]


@dataclass(frozen=True)
class ImportPlan:
    """The import commands to send to Collibra, with the id of the agent version needed to submit the metrics."""

    version_id: str
    commands: list[dict]

