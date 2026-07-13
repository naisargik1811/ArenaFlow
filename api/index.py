"""Vercel serverless entry point.

This module adapts the FastAPI application defined in ``arenaflow.main``
to the AWS Lambda interface expected by Vercel's Python runtime using
``Mangum``. Vercel will invoke the ``handler`` function for each request.
"""

from mangum import Mangum
from arenaflow.main import app as fastapi_app

# Exported handler Vercel will call
handler = Mangum(fastapi_app)
