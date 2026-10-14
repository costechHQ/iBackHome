"""Background jobs for evidence. Owner: Abigail."""

from app.workers.celery_app import celery_app


@celery_app.task(name="evidence.run_checks")  # type: ignore[untyped-decorator]
def run_checks(evidence_id: str) -> None:
    """Run the server checks on one capture (file hash, signature, device, clock, geofence, reuse).

    Day 3 only queues this job. The checks and the accepted/flagged/rejected result are Day 4, so
    until then the evidence stays `pending_checks`. Takes an id, never an object, and is safe to run twice.
    """
    return None
