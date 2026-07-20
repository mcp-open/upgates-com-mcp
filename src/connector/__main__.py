"""`python -m connector` — Dockerfile ENTRYPOINT aj lokálny CLI vstupný bod."""

from __future__ import annotations

from openmcp_sdk import run_connector

from connector.anonymize import require_salt
from connector.server import mcp, test_connection

# Fail-fast: bez PII saltu by pseudonymizácia stratila stabilitu tokenov, a to
# ticho — prejavilo by sa to až po prvom reštarte podu. Radšej nenaštartovať.
require_salt()

run_connector("connector.yaml", mcp, test_connection=test_connection)
