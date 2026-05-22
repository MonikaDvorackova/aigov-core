"""
Thin HTTP client for the GovAI Rust audit API: evidence ingest, bundle, compliance summary,
and hash-chain verification (``GET /verify``).

No business logic beyond HTTP and response handling.
"""

from importlib.metadata import version

__version__ = version("aigov-py")

from .api import get_compliance_summary
from .bundle import get_bundle, get_bundle_hash
from .client import GovAIAPIError, GovAIClient, GovAIError, GovAIHTTPError
from .compliance import (
    current_state_from_summary,
    decision_signals,
    decision_signals_from_summary,
)
from .evidence import submit_event
from .export import export_run
from .usage import get_usage
from .verify import verify_chain

__all__ = [
    "__version__",
    "GovAIAPIError",
    "GovAIClient",
    "GovAIError",
    "GovAIHTTPError",
    "current_state_from_summary",
    "decision_signals",
    "decision_signals_from_summary",
    "get_bundle",
    "get_bundle_hash",
    "get_compliance_summary",
    "get_usage",
    "export_run",
    "submit_event",
    "verify_chain",
]
