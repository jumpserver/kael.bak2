import logging
import json
import datetime as dt
from starlette import status

# Base path configuration - easily changeable
BASE_PATH = "/kael"

from fastapi import (
    Depends,
    Request,
    APIRouter, HTTPException,
)

from open_webui.config import (
    GOOGLE_DRIVE_CLIENT_ID,
    GOOGLE_DRIVE_API_KEY,
    ONEDRIVE_CLIENT_ID,

    # WebUI
    WEBUI_AUTH,
    # Misc
    DEFAULT_LOCALE,
)
from open_webui.env import (
    SRC_LOG_LEVELS,
    VERSION,
    ENABLE_WEBSOCKET_SUPPORT,
)

from open_webui.tasks import (
    list_task_ids_by_chat_id,
    stop_task,
    list_tasks,
)  # Import from tasks.py

from open_webui.utils.models import (
    get_all_models,
    get_all_base_models,
)

from open_webui.models.chats import Chats
from open_webui.utils.auth import get_verified_user
from open_webui.utils.chat import (
    generate_chat_completion as chat_completion_handler,
    chat_completed as chat_completed_handler,
    chat_action as chat_action_handler,
)
from open_webui.utils.middleware import process_chat_payload, process_chat_response

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])

router = APIRouter()
BASE_PATH = "/kael"


def setup_lazy_routes(app):
    # Add direct endpoints with base path
    @app.get(f"{BASE_PATH}/api/models")
    async def get_models(request: Request, user=Depends(get_verified_user)):
        all_models = await get_all_models(request)

        models = []
        for model in all_models:
            # Filter out filter pipelines
            if "pipeline" in model and model["pipeline"].get("type", None) == "filter":
                continue

            try:
                model_tags = [
                    tag.get("name")
                    for tag in model.get("info", {}).get("meta", {}).get("tags", [])
                ]
                tags = [tag.get("name") for tag in model.get("tags", [])]

                tags = list(set(model_tags + tags))
                model["tags"] = [{"name": tag} for tag in tags]
            except Exception as e:
                log.debug(f"Error processing model tags: {e}")
                model["tags"] = []
                pass

            models.append(model)

        model_order_list = request.app.state.config.MODEL_ORDER_LIST
        if model_order_list:
            model_order_dict = {model_id: i for i, model_id in enumerate(model_order_list)}
            # Sort models by order list priority, with fallback for those not in the list
            models.sort(
                key=lambda x: (model_order_dict.get(x["id"], float("inf")), x["name"])
            )

        log.debug(
            f"/api/models returned filtered models accessible to the user: {json.dumps([model['id'] for model in models])}"
        )
        return {"data": models}

    @app.get(f"{BASE_PATH}/api/models/base")
    async def get_base_models(request: Request, user=Depends(get_verified_user)):
        models = await get_all_base_models(request)
        return {"data": models}

    @app.get(f"{BASE_PATH}/api/config")
    async def get_app_config():
        return {
            "status": True,
            "name": app.state.WEBUI_NAME,
            "version": VERSION,
            "default_locale": str(DEFAULT_LOCALE),
            "features": {
                "auth": WEBUI_AUTH,
                "auth_trusted_header": bool(app.state.AUTH_TRUSTED_EMAIL_HEADER),
                "enable_ldap": app.state.config.ENABLE_LDAP,
                "enable_api_key": app.state.config.ENABLE_API_KEY,
                "enable_signup": app.state.config.ENABLE_SIGNUP,
                "enable_login_form": app.state.config.ENABLE_LOGIN_FORM,
                "enable_websocket": ENABLE_WEBSOCKET_SUPPORT,
                "enable_direct_connections": app.state.config.ENABLE_DIRECT_CONNECTIONS,
                "enable_channels": app.state.config.ENABLE_CHANNELS,
                "enable_web_search": app.state.config.ENABLE_WEB_SEARCH,
                "enable_code_execution": app.state.config.ENABLE_CODE_EXECUTION,
                "enable_code_interpreter": app.state.config.ENABLE_CODE_INTERPRETER,
                "enable_image_generation": app.state.config.ENABLE_IMAGE_GENERATION,
                "enable_autocomplete_generation": app.state.config.ENABLE_AUTOCOMPLETE_GENERATION,
                "enable_community_sharing": app.state.config.ENABLE_COMMUNITY_SHARING,
                "enable_message_rating": app.state.config.ENABLE_MESSAGE_RATING,
                "enable_user_webhooks": app.state.config.ENABLE_USER_WEBHOOKS,
                "enable_google_drive_integration": app.state.config.ENABLE_GOOGLE_DRIVE_INTEGRATION,
                "enable_onedrive_integration": app.state.config.ENABLE_ONEDRIVE_INTEGRATION,
            },
            "default_models": app.state.config.DEFAULT_MODELS,
            "default_prompt_suggestions": app.state.config.DEFAULT_PROMPT_SUGGESTIONS,
            "user_count": 1,
            "code": {
                "engine": app.state.config.CODE_EXECUTION_ENGINE,
            },
            "audio": {
                "tts": {
                    "engine": app.state.config.TTS_ENGINE,
                    "voice": app.state.config.TTS_VOICE,
                    "split_on": app.state.config.TTS_SPLIT_ON,
                },
                "stt": {
                    "engine": app.state.config.STT_ENGINE,
                },
            },
            "file": {
                "max_size": app.state.config.FILE_MAX_SIZE,
                "max_count": app.state.config.FILE_MAX_COUNT,
            },
            "permissions": {**app.state.config.USER_PERMISSIONS},
            "google_drive": {
                "client_id": GOOGLE_DRIVE_CLIENT_ID.value,
                "api_key": GOOGLE_DRIVE_API_KEY.value,
            },
            "onedrive": {"client_id": ONEDRIVE_CLIENT_ID.value},
            "active_entries": app.state.USER_COUNT,
        }

    @app.get(f"{BASE_PATH}/api/version")
    async def get_app_version():
        return {
            "version": VERSION,
        }

    @app.get(f"{BASE_PATH}/health/")
    async def health():
        UTC = getattr(dt, "UTC", dt.timezone.utc)
        upTime = dt.datetime.now().astimezone().astimezone(UTC)
        now_utc = dt.datetime.now(UTC)
        return {
            "timestamp": now_utc.isoformat().replace("+00:00", "Z"),  # ISO8601 with Z
            "uptime": str(now_utc - upTime),
        }

    @app.post(f"{BASE_PATH}/api/chat/completions")
    async def chat_completion(
            request: Request,
            form_data: dict,
            user=Depends(get_verified_user),
    ):
        if not request.app.state.MODELS:
            await get_all_models(request)

        model_item = form_data.pop("model_item", {})
        tasks = form_data.pop("background_tasks", None)

        metadata = {}
        try:
            if not model_item.get("direct", False):
                model_id = form_data.get("model", None)
                if model_id not in request.app.state.MODELS:
                    raise Exception("Model not found")

                model = request.app.state.MODELS[model_id]
                model_info = None
            else:
                model = model_item
                model_info = None

                request.state.direct = True
                request.state.model = model

            metadata = {
                "user_id": user.id,
                "chat_id": form_data.pop("chat_id", None),
                "message_id": form_data.pop("id", None),
                "session_id": form_data.pop("session_id", None),
                "tool_ids": form_data.get("tool_ids", None),
                "tool_servers": form_data.pop("tool_servers", None),
                "files": form_data.get("files", None),
                "features": form_data.get("features", None),
                "variables": form_data.get("variables", None),
                "model": model,
                "direct": model_item.get("direct", False),
                **(
                    {"function_calling": "native"}
                    if form_data.get("params", {}).get("function_calling") == "native"
                       or (
                               model_info
                               and model_info.params.model_dump().get("function_calling")
                               == "native"
                       )
                    else {}
                ),
            }

            request.state.metadata = metadata
            form_data["metadata"] = metadata

            form_data, metadata, events = await process_chat_payload(
                request, form_data, user, metadata, model
            )

        except Exception as e:
            log.debug(f"Error processing chat payload: {e}")
            if metadata.get("chat_id") and metadata.get("message_id"):
                # Update the chat message with the error
                Chats.upsert_message_to_chat_by_id_and_message_id(
                    metadata["chat_id"],
                    metadata["message_id"],
                    {
                        "error": {"content": str(e)},
                    },
                )

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )

        try:
            response = await chat_completion_handler(request, form_data, user)

            return await process_chat_response(
                request, response, form_data, user, metadata, model, events, tasks
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )

    # # Alias for chat_completion (Legacy)
    # generate_chat_completions = chat_completion
    # generate_chat_completion = chat_completion

    @app.post(f"{BASE_PATH}/api/chat/completed")
    async def chat_completed(
            request: Request, form_data: dict, user=Depends(get_verified_user)
    ):
        try:
            model_item = form_data.pop("model_item", {})

            if model_item.get("direct", False):
                request.state.direct = True
                request.state.model = model_item

            return await chat_completed_handler(request, form_data, user)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )

    @app.post(f"{BASE_PATH}/api/chat/actions/" + "{action_id}")
    async def chat_action(
            request: Request, action_id: str, form_data: dict, user=Depends(get_verified_user)
    ):
        try:
            model_item = form_data.pop("model_item", {})

            if model_item.get("direct", False):
                request.state.direct = True
                request.state.model = model_item

            return await chat_action_handler(request, action_id, form_data, user)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )

    @app.post(f"{BASE_PATH}/api/tasks/stop/" + "{task_id}")
    async def stop_task_endpoint(task_id: str, user=Depends(get_verified_user)):
        try:
            result = await stop_task(task_id)
            return result
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    @app.get(f"{BASE_PATH}/api/tasks")
    async def list_tasks_endpoint(user=Depends(get_verified_user)):
        return {"tasks": list_tasks()}

    @app.get(f"{BASE_PATH}/api/tasks/chat/" + "{chat_id}")
    async def list_tasks_by_chat_id_endpoint(chat_id: str, user=Depends(get_verified_user)):
        chat = Chats.get_chat_by_id(chat_id)
        if chat is None or chat['user_id'] != user.id:
            return {"task_ids": []}

        task_ids = list_task_ids_by_chat_id(chat_id)

        print(f"Task IDs for chat {chat_id}: {task_ids}")
        return {"task_ids": task_ids}
