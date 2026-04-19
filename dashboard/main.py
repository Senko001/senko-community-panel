import calendar
import logging
import os
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse

from dashboard.auth import create_session, read_session
from dashboard.discord_api import (
    exchange_code,
    get_user,
    get_guilds,
    get_user_by_id,
    get_guild,
    get_member,
    get_bot_user,
    search_members,
    list_members,
    get_roles,
    add_role,
    remove_role,
    timeout_member,
    kick_member,
    ban_member,
)
from dashboard.permissions import (
    get_user_level,
    can_access_dashboard,
    can_moderate,
    can_manage_roles,
    can_manage_warns,
)
from dashboard.storage import (
    init_db,
    add_warn,
    get_warns_for_user,
    delete_warn,
    add_mod_log,
    get_logs_for_guild,
)

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("senko-dashboard")

app = FastAPI()

DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID", "")
DISCORD_REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI", "")


@app.on_event("startup")
async def startup_event():
    try:
        os.makedirs("dashboard", exist_ok=True)
        init_db()
        logger.info("Dashboard startup erfolgreich.")
    except Exception as e:
        logger.exception("Startup Fehler: %s", e)


@app.get("/health")
async def health():
    return {"status": "ok"}
