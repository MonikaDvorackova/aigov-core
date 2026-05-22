from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


class GovaiError(Exception):
    def __init__(self, message: str, status_code: Optional[int] = None, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.status_code = status_code
        self.details = details or {}


@dataclass(frozen=True)
class AssessmentCreate:
    system_name: str
    intended_purpose: str
    risk_class: str
    team_id: Optional[str] = None
    created_by: Optional[str] = None


@dataclass(frozen=True)
class AssessmentOut:
    id: str
    system_name: str
    intended_purpose: str
    risk_class: str
    created_at: Optional[str] = None
