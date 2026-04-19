import calendar
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

app = FastAPI()

import os
DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
DISCORD_REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI")


@app.on_event("startup")
async def startup_event():
    init_db()


def esc(value: str | None) -> str:
    if value is None:
        return ""
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def add_months(dt: datetime, months: int) -> datetime:
    month = dt.month - 1 + months
    year = dt.year + month // 12
    month = month % 12 + 1
    day = min(dt.day, calendar.monthrange(year, month)[1])
    return dt.replace(year=year, month=month, day=day)


def clamp_timeout_until(target: datetime, now: datetime) -> datetime:
    max_until = now + timedelta(days=28)
    return min(target, max_until)


def discord_id_to_datetime(discord_id: str) -> datetime:
    discord_epoch = 1420070400000
    timestamp = ((int(discord_id) >> 22) + discord_epoch) / 1000
    return datetime.fromtimestamp(timestamp, tz=timezone.utc)


def fmt_dt(dt_str: str | None) -> str:
    if not dt_str:
        return "Unbekannt"
    return dt_str.replace("T", " ").replace("+00:00", " UTC")


def avatar_url(user: dict) -> str:
    avatar = user.get("avatar")
    user_id = user["id"]
    if avatar:
        ext = "gif" if str(avatar).startswith("a_") else "png"
        return f"https://cdn.discordapp.com/avatars/{user_id}/{avatar}.{ext}?size=256"
    return f"https://cdn.discordapp.com/embed/avatars/{int(user_id) % 6}.png"


def banner_url(user: dict) -> str | None:
    banner = user.get("banner")
    if not banner:
        return None
    ext = "gif" if str(banner).startswith("a_") else "png"
    return f"https://cdn.discordapp.com/banners/{user['id']}/{banner}.{ext}?size=1024"


def accent_hex(user: dict) -> str | None:
    accent = user.get("accent_color")
    if accent is None:
        return None
    return f"#{accent:06x}"


def layout(title: str, content: str) -> str:
    return f"""
    <!DOCTYPE html>
    <html lang="de">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title}</title>
        <style>
            :root {{
                --bg: #0b1220;
                --panel: rgba(17,24,39,0.82);
                --card: rgba(30,41,59,0.92);
                --card-2: rgba(35,50,74,0.95);
                --text: #f8fafc;
                --muted: #cbd5e1;
                --accent: #5865F2;
                --danger: #dc2626;
                --warn: #d97706;
                --success: #16a34a;
                --border: rgba(255,255,255,0.08);
                --shadow: 0 18px 50px rgba(0,0,0,0.25);
            }}
            * {{ box-sizing: border-box; }}
            body {{
                margin: 0;
                background:
                    radial-gradient(circle at top right, rgba(88,101,242,0.20), transparent 25%),
                    radial-gradient(circle at top left, rgba(59,130,246,0.10), transparent 25%),
                    var(--bg);
                color: var(--text);
                font-family: Inter, Arial, sans-serif;
            }}
            .wrap {{
                max-width: 1450px;
                margin: 0 auto;
                padding: 24px;
            }}
            .topbar {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                gap: 16px;
                margin-bottom: 24px;
                flex-wrap: wrap;
            }}
            .title {{
                font-size: clamp(28px, 3vw, 40px);
                font-weight: 800;
                margin: 0;
            }}
            .subtitle {{
                color: var(--muted);
                margin-top: 8px;
            }}
            .panel {{
                background: var(--panel);
                border: 1px solid var(--border);
                backdrop-filter: blur(12px);
                border-radius: 20px;
                padding: 20px;
                box-shadow: var(--shadow);
            }}
            .card {{
                background: linear-gradient(180deg, var(--card-2), var(--card));
                border: 1px solid var(--border);
                border-radius: 18px;
                padding: 18px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.18);
            }}
            .grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
                gap: 18px;
            }}
            .two-grid {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 18px;
            }}
            .member-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
                gap: 18px;
            }}
            .badge {{
                display: inline-flex;
                align-items: center;
                gap: 8px;
                background: #132033;
                border: 1px solid var(--border);
                color: var(--text);
                padding: 10px 14px;
                border-radius: 999px;
                font-size: 14px;
                margin-top: 10px;
            }}
            .toolbar {{
                display: flex;
                flex-wrap: wrap;
                gap: 12px;
                align-items: center;
                margin-bottom: 18px;
            }}
            input, select, textarea {{
                width: 100%;
                padding: 12px 14px;
                border-radius: 12px;
                border: 1px solid var(--border);
                background: #0f172a;
                color: var(--text);
                outline: none;
            }}
            textarea {{
                min-height: 90px;
                resize: vertical;
            }}
            .toolbar input[type="text"] {{
                max-width: 340px;
            }}
            .toolbar select {{
                max-width: 120px;
            }}
            .btn {{
                display: inline-flex;
                align-items: center;
                justify-content: center;
                gap: 8px;
                border: none;
                border-radius: 12px;
                padding: 12px 16px;
                cursor: pointer;
                text-decoration: none;
                color: white;
                background: var(--accent);
                font-weight: 700;
            }}
            .btn-secondary {{ background: #334155; }}
            .btn-danger {{ background: var(--danger); }}
            .btn-warn {{ background: var(--warn); }}
            .btn-success {{ background: var(--success); }}
            .stack {{
                display: flex;
                flex-direction: column;
                gap: 12px;
            }}
            .row {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 12px;
            }}
            .muted {{ color: var(--muted); }}
            .link {{
                color: #93c5fd;
                text-decoration: none;
            }}
            .section-title {{
                font-size: 24px;
                font-weight: 800;
                margin: 0 0 14px 0;
            }}
            .tiny {{
                font-size: 13px;
                color: var(--muted);
                line-height: 1.6;
            }}
            .empty {{
                color: var(--muted);
                padding: 10px 0;
            }}
            .logs {{
                display: grid;
                gap: 12px;
            }}
            .log-item {{
                background: rgba(30,41,59,0.75);
                border: 1px solid var(--border);
                border-radius: 14px;
                padding: 14px;
            }}
            .spacer {{ height: 14px; }}
            .flash {{
                border-radius: 16px;
                padding: 14px 16px;
                margin-bottom: 18px;
                border: 1px solid var(--border);
                font-weight: 700;
            }}
            .flash-error {{
                background: rgba(220,38,38,0.15);
                color: #fecaca;
            }}
            .flash-success {{
                background: rgba(22,163,74,0.15);
                color: #bbf7d0;
            }}
            .hero-banner {{
                height: 180px;
                border-radius: 18px;
                background: linear-gradient(135deg, #1d4ed8, #5865F2);
                margin-bottom: 16px;
                background-size: cover;
                background-position: center;
            }}
            .hero-user {{
                display: flex;
                gap: 16px;
                align-items: center;
                flex-wrap: wrap;
            }}
            .avatar {{
                width: 92px;
                height: 92px;
                border-radius: 50%;
                border: 4px solid rgba(255,255,255,0.18);
                object-fit: cover;
                background: #0f172a;
            }}
            @media (max-width: 980px) {{
                .two-grid, .row {{
                    grid-template-columns: 1fr;
                }}
                .wrap {{
                    padding: 16px;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="wrap">
            {content}
        </div>
    </body>
    </html>
    """


def flash_redirect(path: str, error: str | None = None, success: str | None = None) -> RedirectResponse:
    params = {}
    if error:
        params["error"] = error
    if success:
        params["success"] = success
    if params:
        sep = "&" if "?" in path else "?"
        path = f"{path}{sep}{urlencode(params)}"
    return RedirectResponse(url=path, status_code=303)


def render_flash(request: Request) -> str:
    error = request.query_params.get("error")
    success = request.query_params.get("success")

    parts = []
    if error:
        parts.append(f"<div class='flash flash-error'>{esc(error)}</div>")
    if success:
        parts.append(f"<div class='flash flash-success'>{esc(success)}</div>")
    return "".join(parts)


async def get_session_data(request: Request):
    session_cookie = request.cookies.get("session")
    if not session_cookie:
        return None
    try:
        return read_session(session_cookie)
    except Exception:
        return None


def top_role_position(member_role_ids: list[str], roles: list[dict]) -> int:
    positions = {str(r['id']): int(r.get('position', 0)) for r in roles}
    if not member_role_ids:
        return 0
    return max(positions.get(str(role_id), 0) for role_id in member_role_ids)


async def can_act_on_target(
    guild_id: str,
    viewer_level: str,
    viewer_member: dict,
    target_member: dict,
    target_user_id: str,
    role_id: str | None = None,
) -> str | None:
    guild = await get_guild(guild_id)
    roles = await get_roles(guild_id)
    bot_user = await get_bot_user()
    bot_member = await get_member(guild_id, bot_user["id"])

    if not guild:
        return "Guild nicht gefunden."

    if str(target_user_id) == str(viewer_member["user"]["id"]):
        return "Du kannst dich selbst nicht moderieren."

    if str(target_user_id) == str(guild.get("owner_id")) and viewer_level != "owner":
        return "Nur Owner darf den Server-Owner moderieren."

    viewer_top = top_role_position(viewer_member.get("roles", []), roles)
    target_top = top_role_position(target_member.get("roles", []), roles)
    bot_top = top_role_position(bot_member.get("roles", []), roles) if bot_member else 0

    if viewer_level != "owner" and target_top >= viewer_top:
        return "Du kannst keine Mitglieder mit gleicher oder höherer Rollen-Hierarchie moderieren."

    if target_top >= bot_top:
        return "Der Bot ist in der Rollenhierarchie zu niedrig."

    if role_id is not None:
        role_positions = {str(r["id"]): int(r.get("position", 0)) for r in roles}
        role_pos = role_positions.get(str(role_id), 0)

        if viewer_level != "owner" and role_pos >= viewer_top:
            return "Du kannst diese Rolle nicht verwalten."

        if role_pos >= bot_top:
            return "Der Bot ist zu niedrig für diese Rolle."

    return None


@app.get("/", response_class=HTMLResponse)
async def home():
    login_url = (
        "https://discord.com/oauth2/authorize"
        f"?client_id={DISCORD_CLIENT_ID}"
        "&response_type=code"
        f"&redirect_uri={DISCORD_REDIRECT_URI}"
        "&scope=identify%20guilds"
    )
    return HTMLResponse(layout(
        "Senko Dashboard",
        f"""
        <div class="topbar">
            <div>
                <h1 class="title">Senko Dashboard</h1>
                <div class="subtitle">Modernes Admin-Panel für Discord-Server.</div>
            </div>
        </div>
        <div class="panel" style="max-width:560px;margin:80px auto 0 auto;text-align:center;">
            <h2 class="section-title">Mit Discord einloggen</h2>
            <p class="muted">Rollen, Moderation, Warns und Logs in einem Panel.</p>
            <div class="spacer"></div>
            <a class="btn" href="{login_url}">Discord Login</a>
        </div>
        """,
    ))


@app.get("/callback")
async def callback(code: str):
    token_data = await exchange_code(code)
    access_token = token_data["access_token"]
    user = await get_user(access_token)

    session_token = create_session(
        {
            "access_token": access_token,
            "user_id": user["id"],
            "username": user["username"],
        }
    )

    response = RedirectResponse(url="/dashboard", status_code=302)
    response.set_cookie("session", session_token, httponly=True, samesite="lax")
    return response


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    session_data = await get_session_data(request)
    if not session_data:
        return RedirectResponse(url="/")

    guilds = await get_guilds(session_data["access_token"])

    guild_cards = ""
    for guild in guilds:
        guild_cards += f"""
        <a href="/server/{guild['id']}" class="link">
            <div class="card">
                <h3 style="margin-top:0;">{esc(guild["name"])}</h3>
                <div class="tiny">Guild ID: {guild["id"]}</div>
            </div>
        </a>
        """

    return HTMLResponse(layout(
        "Dashboard",
        f"""
        <div class="topbar">
            <div>
                <h1 class="title">Dein Dashboard</h1>
                <div class="subtitle">Eingeloggt als: {esc(session_data["username"])}</div>
            </div>
            <a class="btn btn-danger" href="/logout">Logout</a>
        </div>

        <div class="panel">
            <h2 class="section-title">Deine Server</h2>
            <div class="grid">{guild_cards}</div>
        </div>
        """,
    ))


@app.get("/server/{guild_id}", response_class=HTMLResponse)
async def server_page(
    request: Request,
    guild_id: str,
    q: str = "",
    limit: int = 25,
    after: str = "",
):
    session_data = await get_session_data(request)
    if not session_data:
        return RedirectResponse(url="/")

    viewer_member = await get_member(guild_id, session_data["user_id"])
    if not viewer_member:
        return HTMLResponse(layout("Kein Zugriff", "<div class='panel'><h1>Du bist nicht in diesem Server oder der Bot kann dich nicht lesen.</h1></div>"))

    level = get_user_level(viewer_member.get("roles", []))
    if not can_access_dashboard(level):
        return HTMLResponse(layout("Kein Zugriff", "<div class='panel'><h1>Kein Zugriff ❌</h1></div>"))

    error_text = ""
    next_after = ""

    try:
        if q.strip():
            members = await search_members(guild_id, q.strip(), limit=min(limit, 100))
        else:
            members = await list_members(guild_id, limit=min(limit, 100), after=after or None)
            if members:
                next_after = str(members[-1]["user"]["id"])
    except Exception as e:
        members = []
        error_text = str(e)

    member_cards = ""
    for member in members:
        user = member["user"]
        joined_at = fmt_dt(member.get("joined_at"))
        created_at = discord_id_to_datetime(user["id"]).strftime("%Y-%m-%d %H:%M UTC")
        display_name = user.get("global_name") or user["username"]

        member_cards += f"""
        <div class="card">
            <div style="display:flex;gap:12px;align-items:center;">
                <img src="{avatar_url(user)}" alt="avatar" style="width:56px;height:56px;border-radius:50%;object-fit:cover;">
                <div>
                    <h3 style="margin:0;">{esc(display_name)}</h3>
                    <div class="muted">@{esc(user["username"])}</div>
                </div>
            </div>
            <div class="spacer"></div>
            <div class="tiny">User ID: {user["id"]}</div>
            <div class="tiny">Server beigetreten: {joined_at}</div>
            <div class="tiny">Discord erstellt: {created_at}</div>
            <div class="spacer"></div>
            <a class="btn btn-secondary" href="/server/{guild_id}/member/{user['id']}">Profil öffnen</a>
        </div>
        """

    if not member_cards:
        member_cards = f"<div class='empty'>{esc(error_text) if error_text else 'Keine Mitglieder gefunden.'}</div>"

    logs = get_logs_for_guild(guild_id, limit=20)
    logs_html = ""
    for log in logs:
        logs_html += f"""
        <div class="log-item">
            <strong>{esc(log["action"]).upper()}</strong>
            <div class="tiny">Target: {esc(log["target_user_id"])} | Mod: {esc(log["moderator_user_id"])}</div>
            <div class="tiny">Reason: {esc(log["reason"] or "—")}</div>
            <div class="tiny">Meta: {esc(log["metadata"] or "—")}</div>
            <div class="tiny">{esc(log["created_at"])}</div>
        </div>
        """
    if not logs_html:
        logs_html = "<div class='empty'>Noch keine Logs.</div>"

    next_button = ""
    if next_after and not q.strip():
        next_button = f'<a class="btn btn-secondary" href="/server/{guild_id}?limit={limit}&after={next_after}">Nächste Seite</a>'

    return HTMLResponse(layout(
        "Server Panel",
        f"""
        <div class="topbar">
            <div>
                <a class="link" href="/dashboard">← Zurück</a>
                <h1 class="title">Server Panel</h1>
                <div class="badge">Dein Rang im Dashboard: {level}</div>
            </div>
        </div>

        {render_flash(request)}

        <div class="panel">
            <h2 class="section-title">Mitglieder</h2>
            <form method="get" class="toolbar">
                <input type="text" name="q" value="{esc(q)}" placeholder="Member suchen...">
                <select name="limit">
                    <option value="10" {"selected" if str(limit) == "10" else ""}>10</option>
                    <option value="25" {"selected" if str(limit) == "25" else ""}>25</option>
                    <option value="50" {"selected" if str(limit) == "50" else ""}>50</option>
                    <option value="100" {"selected" if str(limit) == "100" else ""}>100</option>
                </select>
                <button class="btn" type="submit">Laden</button>
                <a class="btn btn-secondary" href="/server/{guild_id}">Reset</a>
                {next_button}
            </form>
            <div class="member-grid">
                {member_cards}
            </div>
        </div>

        <div class="spacer"></div>

        <div class="panel">
            <h2 class="section-title">Moderation Logs</h2>
            <div class="logs">
                {logs_html}
            </div>
        </div>
        """,
    ))


@app.get("/server/{guild_id}/member/{user_id}", response_class=HTMLResponse)
async def member_profile(request: Request, guild_id: str, user_id: str):
    session_data = await get_session_data(request)
    if not session_data:
        return RedirectResponse(url="/")

    viewer_member = await get_member(guild_id, session_data["user_id"])
    if not viewer_member:
        return RedirectResponse(url="/dashboard")

    level = get_user_level(viewer_member.get("roles", []))
    if not can_access_dashboard(level):
        return HTMLResponse(layout("Kein Zugriff", "<div class='panel'><h1>Kein Zugriff ❌</h1></div>"))

    member = await get_member(guild_id, user_id)
    if not member:
        return HTMLResponse(layout("Nicht gefunden", "<div class='panel'><h1>Mitglied nicht gefunden.</h1></div>"))

    full_user = await get_user_by_id(user_id) or member["user"]
    roles = await get_roles(guild_id)
    role_map = {r["id"]: r["name"] for r in roles}
    current_roles = member.get("roles", [])
    current_role_names = [role_map.get(rid, rid) for rid in current_roles]

    role_options = "".join(
        f"<option value='{r['id']}'>{esc(r['name'])}</option>"
        for r in roles
        if r["name"] != "@everyone"
    )

    display_name = full_user.get("global_name") or full_user["username"]
    created_at = discord_id_to_datetime(full_user["id"]).strftime("%Y-%m-%d %H:%M UTC")
    joined_at = fmt_dt(member.get("joined_at"))
    role_html = "".join([f"<li>{esc(r)}</li>" for r in current_role_names]) or "<li>Keine Rollen</li>"

    warns = get_warns_for_user(guild_id, user_id)
    warns_html = ""
    for warn in warns:
        warns_html += f"""
        <div class="log-item">
            <strong>Warn #{warn["id"]}</strong>
            <div class="tiny">Moderator: {esc(warn["moderator_id"])}</div>
            <div class="tiny">Reason: {esc(warn["reason"] or "—")}</div>
            <div class="tiny">{esc(warn["created_at"])}</div>
            <form method="post" action="/action/delete-warn" style="margin-top:10px;">
                <input type="hidden" name="guild_id" value="{guild_id}">
                <input type="hidden" name="user_id" value="{user_id}">
                <input type="hidden" name="warn_id" value="{warn["id"]}">
                <button class="btn btn-danger" type="submit">Warn löschen</button>
            </form>
        </div>
        """
    if not warns_html:
        warns_html = "<div class='empty'>Keine Warns vorhanden.</div>"

    banner = banner_url(full_user)
    accent = accent_hex(full_user)
    banner_style = f"background-image:url('{banner}');" if banner else f"background:{accent or 'linear-gradient(135deg,#1d4ed8,#5865F2)'};"
    avatar = avatar_url(full_user)

    moderation_html = ""
    if can_moderate(level):
        moderation_html = f"""
        <div class="panel">
            <h2 class="section-title">Moderation</h2>

            <div class="grid">
                <div class="card">
                    <h3>Timeout / Untimeout</h3>
                    <form method="post" action="/action/timeout" class="stack">
                        <input type="hidden" name="guild_id" value="{guild_id}">
                        <input type="hidden" name="user_id" value="{full_user["id"]}">
                        <div class="row">
                            <input type="number" name="duration_value" min="1" placeholder="Dauer" required>
                            <select name="duration_unit">
                                <option value="minutes">Minuten</option>
                                <option value="hours">Stunden</option>
                                <option value="days">Tage</option>
                                <option value="weeks">Wochen</option>
                                <option value="months">Monate</option>
                            </select>
                        </div>
                        <input type="text" name="reason" placeholder="Reason optional">
                        <div class="tiny">Maximal 28 Tage per Discord-API.</div>
                        <button class="btn" type="submit">Timeout setzen</button>
                    </form>

                    <div class="spacer"></div>

                    <form method="post" action="/action/untimeout" class="stack">
                        <input type="hidden" name="guild_id" value="{guild_id}">
                        <input type="hidden" name="user_id" value="{full_user["id"]}">
                        <button class="btn btn-secondary" type="submit">Untimeout</button>
                    </form>
                </div>

                <div class="card">
                    <h3>Kick / Ban</h3>
                    <form method="post" action="/action/kick" class="stack">
                        <input type="hidden" name="guild_id" value="{guild_id}">
                        <input type="hidden" name="user_id" value="{full_user["id"]}">
                        <input type="text" name="reason" placeholder="Reason optional">
                        <button class="btn btn-warn" type="submit">Kick</button>
                    </form>

                    <div class="spacer"></div>

                    <form method="post" action="/action/ban" class="stack">
                        <input type="hidden" name="guild_id" value="{guild_id}">
                        <input type="hidden" name="user_id" value="{full_user["id"]}">
                        <input type="text" name="reason" placeholder="Reason optional">
                        <button class="btn btn-danger" type="submit">Ban</button>
                    </form>
                </div>
            </div>
        </div>
        """

    role_manage_html = ""
    if can_manage_roles(level):
        role_manage_html = f"""
        <div class="panel">
            <h2 class="section-title">Rollen verwalten</h2>
            <div class="grid">
                <div class="card">
                    <h3>Rolle geben</h3>
                    <form method="post" action="/action/add-role" class="stack">
                        <input type="hidden" name="guild_id" value="{guild_id}">
                        <input type="hidden" name="user_id" value="{full_user["id"]}">
                        <select name="role_id" required>
                            {role_options}
                        </select>
                        <input type="text" name="reason" placeholder="Reason optional">
                        <button class="btn btn-success" type="submit">Rolle geben</button>
                    </form>
                </div>

                <div class="card">
                    <h3>Rolle entfernen</h3>
                    <form method="post" action="/action/remove-role" class="stack">
                        <input type="hidden" name="guild_id" value="{guild_id}">
                        <input type="hidden" name="user_id" value="{full_user["id"]}">
                        <select name="role_id" required>
                            {role_options}
                        </select>
                        <input type="text" name="reason" placeholder="Reason optional">
                        <button class="btn btn-danger" type="submit">Rolle entfernen</button>
                    </form>
                </div>
            </div>
        </div>
        """

    warns_manage_html = ""
    if can_manage_warns(level):
        warns_manage_html = f"""
        <div class="panel">
            <h2 class="section-title">Warn-System</h2>
            <div class="grid">
                <div class="card">
                    <h3>Warn geben</h3>
                    <form method="post" action="/action/add-warn" class="stack">
                        <input type="hidden" name="guild_id" value="{guild_id}">
                        <input type="hidden" name="user_id" value="{full_user["id"]}">
                        <textarea name="reason" placeholder="Reason"></textarea>
                        <button class="btn btn-warn" type="submit">Warn speichern</button>
                    </form>
                </div>
                <div class="card">
                    <h3>Warn-Historie</h3>
                    {warns_html}
                </div>
            </div>
        </div>
        """

    return HTMLResponse(layout(
        "Member Profil",
        f"""
        <div class="topbar">
            <div>
                <a class="link" href="/server/{guild_id}">← Zurück</a>
                <h1 class="title">Mitglied Profil</h1>
                <div class="subtitle">{esc(display_name)} · @{esc(full_user["username"])}</div>
            </div>
        </div>

        {render_flash(request)}

        <div class="panel">
            <div class="hero-banner" style="{banner_style}"></div>
            <div class="hero-user">
                <img class="avatar" src="{avatar}" alt="avatar">
                <div>
                    <h2 style="margin:0;">{esc(display_name)}</h2>
                    <div class="muted">@{esc(full_user["username"])}</div>
                    <div class="badge">User ID: {full_user["id"]}</div>
                </div>
            </div>
        </div>

        <div class="spacer"></div>

        <div class="two-grid">
            <div class="panel">
                <h2 class="section-title">Basisdaten</h2>
                <div class="tiny">Name: {esc(display_name)}</div>
                <div class="tiny">@{esc(full_user["username"])}</div>
                <div class="tiny">User ID: {full_user["id"]}</div>
                <div class="tiny">Discord erstellt: {created_at}</div>
                <div class="tiny">Server beigetreten: {joined_at}</div>
                <div class="tiny">Banner vorhanden: {"Ja" if full_user.get("banner") else "Nein"}</div>
            </div>

            <div class="panel">
                <h2 class="section-title">Rollen</h2>
                <ul>{role_html}</ul>
            </div>
        </div>

        <div class="spacer"></div>
        {moderation_html}
        <div class="spacer"></div>
        {role_manage_html}
        <div class="spacer"></div>
        {warns_manage_html}
        """,
    ))


@app.post("/action/kick")
async def kick_user(request: Request):
    session_data = await get_session_data(request)
    form = await request.form()
    user_id = str(form.get("user_id"))
    guild_id = str(form.get("guild_id"))
    reason = form.get("reason")

    viewer_member = await get_member(guild_id, session_data["user_id"])
    target_member = await get_member(guild_id, user_id)
    level = get_user_level(viewer_member.get("roles", []))

    if not can_moderate(level):
        return flash_redirect(f"/server/{guild_id}/member/{user_id}", error="Keine Berechtigung.")

    check = await can_act_on_target(guild_id, level, viewer_member, target_member, user_id)
    if check:
        return flash_redirect(f"/server/{guild_id}/member/{user_id}", error=check)

    try:
        await kick_member(guild_id, user_id, reason)
        add_mod_log(
            guild_id=guild_id,
            target_user_id=user_id,
            moderator_user_id=session_data["user_id"],
            action="kick",
            reason=reason,
            metadata=None,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        return flash_redirect(f"/server/{guild_id}", success="Mitglied wurde gekickt.")
    except httpx.HTTPStatusError as e:
        return flash_redirect(f"/server/{guild_id}/member/{user_id}", error=f"Kick fehlgeschlagen: {e.response.status_code}")


@app.post("/action/timeout")
async def timeout_user(request: Request):
    session_data = await get_session_data(request)
    form = await request.form()
    user_id = str(form.get("user_id"))
    guild_id = str(form.get("guild_id"))
    reason = form.get("reason")
    duration_value = int(form.get("duration_value"))
    duration_unit = form.get("duration_unit")

    viewer_member = await get_member(guild_id, session_data["user_id"])
    target_member = await get_member(guild_id, user_id)
    level = get_user_level(viewer_member.get("roles", []))

    if not can_moderate(level):
        return flash_redirect(f"/server/{guild_id}/member/{user_id}", error="Keine Berechtigung.")

    check = await can_act_on_target(guild_id, level, viewer_member, target_member, user_id)
    if check:
        return flash_redirect(f"/server/{guild_id}/member/{user_id}", error=check)

    now = datetime.now(timezone.utc)

    if duration_unit == "minutes":
        until = now + timedelta(minutes=duration_value)
    elif duration_unit == "hours":
        until = now + timedelta(hours=duration_value)
    elif duration_unit == "days":
        until = now + timedelta(days=duration_value)
    elif duration_unit == "weeks":
        until = now + timedelta(weeks=duration_value)
    elif duration_unit == "months":
        until = add_months(now, duration_value)
    else:
        until = now + timedelta(minutes=10)

    until = clamp_timeout_until(until, now)

    try:
        await timeout_member(guild_id, user_id, until.isoformat(), reason)
        add_mod_log(
            guild_id=guild_id,
            target_user_id=user_id,
            moderator_user_id=session_data["user_id"],
            action="timeout",
            reason=reason,
            metadata=f"until={until.isoformat()}",
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        return flash_redirect(f"/server/{guild_id}/member/{user_id}", success="Timeout gesetzt.")
    except httpx.HTTPStatusError as e:
        return flash_redirect(f"/server/{guild_id}/member/{user_id}", error=f"Timeout fehlgeschlagen: {e.response.status_code}")


@app.post("/action/untimeout")
async def untimeout_user(request: Request):
    session_data = await get_session_data(request)
    form = await request.form()
    user_id = str(form.get("user_id"))
    guild_id = str(form.get("guild_id"))

    viewer_member = await get_member(guild_id, session_data["user_id"])
    target_member = await get_member(guild_id, user_id)
    level = get_user_level(viewer_member.get("roles", []))

    if not can_moderate(level):
        return flash_redirect(f"/server/{guild_id}/member/{user_id}", error="Keine Berechtigung.")

    check = await can_act_on_target(guild_id, level, viewer_member, target_member, user_id)
    if check:
        return flash_redirect(f"/server/{guild_id}/member/{user_id}", error=check)

    try:
        await timeout_member(guild_id, user_id, None, "Dashboard Untimeout")
        add_mod_log(
            guild_id=guild_id,
            target_user_id=user_id,
            moderator_user_id=session_data["user_id"],
            action="untimeout",
            reason="Dashboard Untimeout",
            metadata=None,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        return flash_redirect(f"/server/{guild_id}/member/{user_id}", success="Timeout entfernt.")
    except httpx.HTTPStatusError as e:
        return flash_redirect(f"/server/{guild_id}/member/{user_id}", error=f"Untimeout fehlgeschlagen: {e.response.status_code}")


@app.post("/action/ban")
async def ban_user(request: Request):
    session_data = await get_session_data(request)
    form = await request.form()
    user_id = str(form.get("user_id"))
    guild_id = str(form.get("guild_id"))
    reason = form.get("reason")

    viewer_member = await get_member(guild_id, session_data["user_id"])
    target_member = await get_member(guild_id, user_id)
    level = get_user_level(viewer_member.get("roles", []))

    if not can_moderate(level):
        return flash_redirect(f"/server/{guild_id}/member/{user_id}", error="Keine Berechtigung.")

    check = await can_act_on_target(guild_id, level, viewer_member, target_member, user_id)
    if check:
        return flash_redirect(f"/server/{guild_id}/member/{user_id}", error=check)

    try:
        await ban_member(guild_id, user_id, reason)
        add_mod_log(
            guild_id=guild_id,
            target_user_id=user_id,
            moderator_user_id=session_data["user_id"],
            action="ban",
            reason=reason,
            metadata=None,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        return flash_redirect(f"/server/{guild_id}", success="Mitglied wurde gebannt.")
    except httpx.HTTPStatusError as e:
        return flash_redirect(f"/server/{guild_id}/member/{user_id}", error=f"Ban fehlgeschlagen: {e.response.status_code}")


@app.post("/action/add-role")
async def add_role_action(
    request: Request,
    guild_id: str = Form(...),
    user_id: str = Form(...),
    role_id: str = Form(...),
    reason: str = Form(""),
):
    session_data = await get_session_data(request)
    viewer_member = await get_member(guild_id, session_data["user_id"])
    target_member = await get_member(guild_id, user_id)
    level = get_user_level(viewer_member.get("roles", []))

    if not can_manage_roles(level):
        return flash_redirect(f"/server/{guild_id}/member/{user_id}", error="Keine Berechtigung.")

    check = await can_act_on_target(guild_id, level, viewer_member, target_member, user_id, role_id)
    if check:
        return flash_redirect(f"/server/{guild_id}/member/{user_id}", error=check)

    try:
        await add_role(guild_id, user_id, role_id, reason)
        add_mod_log(
            guild_id=guild_id,
            target_user_id=user_id,
            moderator_user_id=session_data["user_id"],
            action="add_role",
            reason=reason,
            metadata=f"role_id={role_id}",
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        return flash_redirect(f"/server/{guild_id}/member/{user_id}", success="Rolle hinzugefügt.")
    except httpx.HTTPStatusError as e:
        return flash_redirect(f"/server/{guild_id}/member/{user_id}", error=f"Rolle konnte nicht hinzugefügt werden: {e.response.status_code}")


@app.post("/action/remove-role")
async def remove_role_action(
    request: Request,
    guild_id: str = Form(...),
    user_id: str = Form(...),
    role_id: str = Form(...),
    reason: str = Form(""),
):
    session_data = await get_session_data(request)
    viewer_member = await get_member(guild_id, session_data["user_id"])
    target_member = await get_member(guild_id, user_id)
    level = get_user_level(viewer_member.get("roles", []))

    if not can_manage_roles(level):
        return flash_redirect(f"/server/{guild_id}/member/{user_id}", error="Keine Berechtigung.")

    check = await can_act_on_target(guild_id, level, viewer_member, target_member, user_id, role_id)
    if check:
        return flash_redirect(f"/server/{guild_id}/member/{user_id}", error=check)

    try:
        await remove_role(guild_id, user_id, role_id, reason)
        add_mod_log(
            guild_id=guild_id,
            target_user_id=user_id,
            moderator_user_id=session_data["user_id"],
            action="remove_role",
            reason=reason,
            metadata=f"role_id={role_id}",
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        return flash_redirect(f"/server/{guild_id}/member/{user_id}", success="Rolle entfernt.")
    except httpx.HTTPStatusError as e:
        return flash_redirect(f"/server/{guild_id}/member/{user_id}", error=f"Rolle konnte nicht entfernt werden: {e.response.status_code}")


@app.post("/action/add-warn")
async def add_warn_action(
    request: Request,
    guild_id: str = Form(...),
    user_id: str = Form(...),
    reason: str = Form(""),
):
    session_data = await get_session_data(request)
    viewer = await get_member(guild_id, session_data["user_id"])
    if not can_manage_warns(get_user_level(viewer.get("roles", []))):
        return flash_redirect(f"/server/{guild_id}/member/{user_id}", error="Keine Berechtigung.")

    add_warn(
        guild_id=guild_id,
        user_id=user_id,
        moderator_id=session_data["user_id"],
        reason=reason,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    add_mod_log(
        guild_id=guild_id,
        target_user_id=user_id,
        moderator_user_id=session_data["user_id"],
        action="warn",
        reason=reason,
        metadata=None,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    return flash_redirect(f"/server/{guild_id}/member/{user_id}", success="Warn gespeichert.")


@app.post("/action/delete-warn")
async def delete_warn_action(
    request: Request,
    guild_id: str = Form(...),
    user_id: str = Form(...),
    warn_id: int = Form(...),
):
    delete_warn(warn_id)
    return flash_redirect(f"/server/{guild_id}/member/{user_id}", success="Warn gelöscht.")


@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie("session")
    return response
