import logging
import sys
import datetime as dt

# Base path configuration - easily changeable
BASE_PATH = "/kael"

from fastapi import APIRouter
from fastapi.staticfiles import StaticFiles

from open_webui.config import STATIC_DIR, CACHE_DIR
from open_webui.env import GLOBAL_LOG_LEVEL, SRC_LOG_LEVELS
from open_webui.views.common import setup_lazy_routes
from open_webui.views import (
    audio,
    images,
    ollama,
    openai,
    retrieval,
    pipelines,
    tasks,
    auths,
    channels,
    chats,
    folders,
    configs,
    groups,
    files,
    functions,
    memories,
    models,
    knowledge,
    prompts,
    evaluations,
    tools,
    users,
    utils,
)

logging.basicConfig(stream=sys.stdout, level=GLOBAL_LOG_LEVEL)
log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])


def setup_routes(app, socket_app):
    """
    Setup all routes for the FastAPI application using APIRouter.
    This provides a clean way to organize routes and easily change the base path.
    """
    # Create main API router
    main_router = APIRouter()

    # Include all sub-views with their prefixes
    main_router.include_router(ollama.router, prefix="/ollama", tags=["ollama"])
    main_router.include_router(openai.router, prefix="/openai", tags=["openai"])

    main_router.include_router(pipelines.router, prefix="/api/v1/pipelines", tags=["pipelines"])
    main_router.include_router(tasks.router, prefix="/api/v1/tasks", tags=["tasks"])
    main_router.include_router(images.router, prefix="/api/v1/images", tags=["images"])

    main_router.include_router(audio.router, prefix="/api/v1/audio", tags=["audio"])
    main_router.include_router(retrieval.router, prefix="/api/v1/retrieval", tags=["retrieval"])

    main_router.include_router(configs.router, prefix="/api/v1/configs", tags=["configs"])

    main_router.include_router(auths.router, prefix="/api/v1/auths", tags=["auths"])
    main_router.include_router(users.router, prefix="/api/v1/users", tags=["users"])

    main_router.include_router(channels.router, prefix="/api/v1/channels", tags=["channels"])
    main_router.include_router(chats.router, prefix="/api/v1/chats", tags=["chats"])

    main_router.include_router(models.router, prefix="/api/v1/models", tags=["models"])
    main_router.include_router(knowledge.router, prefix="/api/v1/knowledge", tags=["knowledge"])
    main_router.include_router(prompts.router, prefix="/api/v1/prompts", tags=["prompts"])
    main_router.include_router(tools.router, prefix="/api/v1/tools", tags=["tools"])

    main_router.include_router(memories.router, prefix="/api/v1/memories", tags=["memories"])
    main_router.include_router(folders.router, prefix="/api/v1/folders", tags=["folders"])
    main_router.include_router(groups.router, prefix="/api/v1/groups", tags=["groups"])
    main_router.include_router(files.router, prefix="/api/v1/files", tags=["files"])
    main_router.include_router(functions.router, prefix="/api/v1/functions", tags=["functions"])
    main_router.include_router(evaluations.router, prefix="/api/v1/evaluations", tags=["evaluations"])
    main_router.include_router(utils.router, prefix="/api/v1/utils", tags=["utils"])

    setup_lazy_routes(app)

    # Mount WebSocket and main router with base path
    app.mount(f"{BASE_PATH}/ws", socket_app)
    app.include_router(main_router, prefix=BASE_PATH)

    app.mount(f"{BASE_PATH}/kael", StaticFiles(directory=STATIC_DIR), name="kael")
    app.mount(f"{BASE_PATH}/static", StaticFiles(directory=STATIC_DIR), name="static")
    app.mount(f"{BASE_PATH}/cache", StaticFiles(directory=CACHE_DIR), name="cache")

    return app
