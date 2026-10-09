"""HTTP endpoints for payments. Owner: Gabriel.

Routes are mounted under /api/v1 automatically; parse the request, check permissions,
call service.py, and return a schema. Keep business rules out of this file.
"""

from fastapi import APIRouter

router = APIRouter(tags=["payments"])
