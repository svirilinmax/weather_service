import time
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("weather_logger")


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.time()

        logger.info(
            f"action='request_start' "
            f"method={request.method} "
            f"path={request.url.path} "
            f"client_ip={request.client.host if request.client else 'unknown'}"
        )

        try:
            response = await call_next(request)
            duration_ms = round((time.time() - start_time) * 1000, 2)

            logger.info(
                f"action='request_end' "
                f"method={request.method} "
                f"path={request.url.path} "
                f"status_code={response.status_code} "
                f"duration_ms={duration_ms}"
            )

            return response
        except Exception as e:
            duration_ms = round((time.time() - start_time) * 1000, 2)
            logger.error(
                f"action='request_error' "
                f"method={request.method} "
                f"path={request.url.path} "
                f"error='{str(e)}' "
                f"duration_ms={duration_ms}"
            )
            raise