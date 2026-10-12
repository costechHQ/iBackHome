"""HTTP endpoints for audit. Owner: Lilian.

Routes are mounted under /api/v1 automatically; parse the request, check permissions,
call service.py, and return a schema. Keep business rules out of this file.
"""
