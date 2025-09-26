import logging
import json
import datetime as dt

# Base path configuration - easily changeable
BASE_PATH = "/kael"

from fastapi import (
    Depends,
    Request,
    APIRouter,
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

from open_webui.utils.models import (
    get_all_models,
    get_all_base_models,
)

from open_webui.utils.auth import (
    get_verified_user,
)

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
        models = await get_all_base_models(request, user=user)
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
    