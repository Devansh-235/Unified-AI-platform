from dataclasses import dataclass
from typing import TypedDict


@dataclass(frozen=True)
class Attachment:
    name: str
    data: bytes


class PlatformError(Exception):
    """A safe, actionable message suitable for the interface."""


class State(TypedDict, total=False):
    question: str
    attachments: list[Attachment]
    documents: list[Attachment]
    route: str
    reason: str
    response: str
    payload: dict
    error: bool
    trace: list[str]
