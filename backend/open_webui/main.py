import asyncio
import logging
import mimetypes
import os
import sys
from contextlib import asynccontextmanager

# Base path configuration - easily changeable
BASE_PATH = "/kael"


from fastapi import (
    FastAPI,
    HTTPException,
    applications,
)

from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.staticfiles import StaticFiles

from starlette.exceptions import HTTPException as StarletteHTTPException

from open_webui.utils.logger import start_logger
from open_webui.socket.main import (
    app as socket_app,
    periodic_usage_pool_cleanup,
)
from open_webui.config.app import init_app_config
from open_webui.middlewares import init_middlewares
from open_webui.urls import setup_routes


from open_webui.models.functions import Functions

from open_webui.config import (
    # Misc
    ENV,
    FRONTEND_BUILD_DIR,
)
from open_webui.env import (
    GLOBAL_LOG_LEVEL,
    SAFE_MODE,
    SRC_LOG_LEVELS,
)



if SAFE_MODE:
    print("SAFE MODE ENABLED")
    Functions.deactivate_all_functions()

logging.basicConfig(stream=sys.stdout, level=GLOBAL_LOG_LEVEL)
log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])


class SPAStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        try:
            return await super().get_response(path, scope)
        except (HTTPException, StarletteHTTPException) as ex:
            if ex.status_code == 404:
                if path.endswith(".js"):
                    # Return 404 for javascript files
                    raise ex
                else:
                    return await super().get_response("index.html", scope)
            else:
                raise ex

@asynccontextmanager
async def lifespan(app: FastAPI):
    start_logger()

    asyncio.create_task(periodic_usage_pool_cleanup())
    yield


app = FastAPI(
    title="JumpServer Chat",
    docs_url="/docs" if ENV == "dev" else None,
    openapi_url="/openapi.json" if ENV == "dev" else None,
    redoc_url=None,
    lifespan=lifespan,
)

init_app_config(app)
init_middlewares(app)
# Setup all routes
setup_routes(app, socket_app)



def swagger_ui_html(*args, **kwargs):
    return get_swagger_ui_html(
        *args,
        **kwargs,
        swagger_js_url="/static/swagger-ui/swagger-ui-bundle.js",
        swagger_css_url="/static/swagger-ui/swagger-ui.css",
        swagger_favicon_url="/static/swagger-ui/favicon.png",
    )


applications.get_swagger_ui_html = swagger_ui_html

if os.path.exists(FRONTEND_BUILD_DIR):
    mimetypes.add_type("text/javascript", ".js")
    app.mount(
        BASE_PATH,
        SPAStaticFiles(directory=FRONTEND_BUILD_DIR, html=True),
        name="spa-static-files",
    )
else:
    log.warning(
        f"Frontend build directory not found at '{FRONTEND_BUILD_DIR}'. Serving API only."
    )
