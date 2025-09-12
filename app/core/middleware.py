"""HTTP request logging middleware."""

import logging
import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log HTTP requests and responses."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process HTTP request and log details."""
        start_time = time.time()

        # Extract request details
        method = request.method
        url = str(request.url)
        client_ip = request.client.host if request.client else "unknown"
        user_agent = request.headers.get("user-agent", "")

        # Log incoming request
        logger.info(
            f"Request started: {method} {url}",
            extra={
                "method": method,
                "url": url,
                "client_ip": client_ip,
                "user_agent": user_agent,
            },
        )

        try:
            # Process request
            response = await call_next(request)

            # Calculate processing time
            process_time = time.time() - start_time

            # Log response
            logger.info(
                f"Request completed: {method} {url} - {response.status_code} - {process_time:.3f}s",
                extra={
                    "method": method,
                    "url": url,
                    "status_code": response.status_code,
                    "process_time": process_time,
                    "client_ip": client_ip,
                },
            )

            # Add processing time header
            response.headers["X-Process-Time"] = str(process_time)

            return response

        except Exception as e:
            # Calculate processing time for failed requests
            process_time = time.time() - start_time

            # Log error
            logger.error(
                f"Request failed: {method} {url} - {str(e)} - {process_time:.3f}s",
                extra={
                    "method": method,
                    "url": url,
                    "error": str(e),
                    "process_time": process_time,
                    "client_ip": client_ip,
                },
                exc_info=True,
            )

            # Re-raise the exception
            raise
