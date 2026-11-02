"""Supervision messages. Owner: James.

Spot check assigned (spec: supervisor, push + SMS). Only the visiting supervisor is told: a spot check is
unannounced, so nothing about it ever goes to the contractor or the project's own supervisor.
"""

from app.base.notifications import Template

SPOT_CHECK_ASSIGNED = Template(
    name="spot_check.assigned",
    title="New spot check",
    text="New spot check: please visit {project} on {when}. Open iBackHome for the details.",
)
