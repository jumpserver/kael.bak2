import time
import os
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from urllib.parse import parse_qs, urlparse, urlencode
from fastapi.responses import RedirectResponse
from starlette.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette import status

from open_webui.utils.security_headers import SecurityHeadersMiddleware
from open_webui.utils.audit import AuditLevel, AuditLoggingMiddleware
from open_webui.env import AUDIT_LOG_LEVEL, AUDIT_EXCLUDED_PATHS, MAX_BODY_LOG_SIZE
from open_webui.utils.logger import logger
from open_webui.utils.auth import get_http_authorization_cred
from open_webui.internal.db import Session

BASE_PATH = '/kael'
CORS_ALLOW_ORIGIN = os.environ.get("CORS_ALLOW_ORIGIN", "*")


class RedirectMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Check if the request is a GET request
        if request.method == "GET":
            path = request.url.path
            query_params = dict(parse_qs(urlparse(str(request.url)).query))

            # Check for the specific watch path and the presence of 'v' parameter
            if path.endswith("/watch") and "v" in query_params:
                video_id = query_params["v"][0]  # Extract the first 'v' parameter
                encoded_video_id = urlencode({"youtube": video_id})
                redirect_url = f"/?{encoded_video_id}"
                return RedirectResponse(url=redirect_url)

        # Proceed with the normal flow of other requests
        response = await call_next(request)
        return response


def init_middlewares(app):
    # Add the middleware to the app
    app.add_middleware(RedirectMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)

    @app.middleware("http")
    async def commit_session_after_request(request: Request, call_next):
        response = await call_next(request)
        # log.debug("Commit session after request")
        Session.commit()
        return response

    @app.middleware("http")
    async def check_url(request: Request, call_next):
        start_time = int(time.time())
        request.state.token = get_http_authorization_cred(
            request.headers.get("Authorization")
        )

        request.state.enable_api_key = app.state.config.ENABLE_API_KEY
        response = await call_next(request)
        process_time = int(time.time()) - start_time
        response.headers["X-Process-Time"] = str(process_time)
        return response

    @app.middleware("http")
    async def inspect_websocket(request: Request, call_next):
        if (
                f"{BASE_PATH}/ws/socket.io" in request.url.path
                and request.query_params.get("transport") == "websocket"
        ):
            upgrade = (request.headers.get("Upgrade") or "").lower()
            connection = (request.headers.get("Connection") or "").lower().split(",")
            # Check that there's the correct headers for an upgrade, else reject the connection
            # This is to work around this upstream issue: https://github.com/miguelgrinberg/python-engineio/issues/367
            if upgrade != "websocket" or "upgrade" not in connection:
                return JSONResponse(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    content={"detail": "Invalid WebSocket upgrade request"},
                )
        return await call_next(request)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ALLOW_ORIGIN,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    try:
        audit_level = AuditLevel(AUDIT_LOG_LEVEL)
    except ValueError as e:
        logger.error(f"Invalid audit level: {AUDIT_LOG_LEVEL}. Error: {e}")
        audit_level = AuditLevel.NONE

    if audit_level != AuditLevel.NONE:
        app.add_middleware(
            AuditLoggingMiddleware,
            audit_level=audit_level,
            excluded_paths=AUDIT_EXCLUDED_PATHS,
            max_body_size=MAX_BODY_LOG_SIZE,
        )
