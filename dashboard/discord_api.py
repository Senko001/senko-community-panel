import os
import httpx
from dotenv import load_dotenv

load_dotenv()

DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")
DISCORD_REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI")
DISCORD_BOT_TOKEN = os.getenv("DISCORD_TOKEN")

DISCORD_API = "https://discord.com/api/v10"

async def exchange_code(code: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{DISCORD_API}/oauth2/token",
            data={
                "client_id": DISCORD_CLIENT_ID,
                "client_secret": DISCORD_CLIENT_SECRET,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": DISCORD_REDIRECT_URI,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        response.raise_for_status()
        return response.json()

async def get_user(access_token: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{DISCORD_API}/users/@me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        response.raise_for_status()
        return response.json()

async def get_guilds(access_token: str) -> list:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{DISCORD_API}/users/@me/guilds",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        response.raise_for_status()
        return response.json()

def bot_headers(reason: str | None = None) -> dict:
    headers = {
        "Authorization": f"Bot {DISCORD_BOT_TOKEN}",
        "Content-Type": "application/json",
    }
    if reason and reason.strip():
        headers["X-Audit-Log-Reason"] = reason.strip()
    return headers

async def get_bot_user() -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{DISCORD_API}/users/@me",
            headers=bot_headers(),
        )
        response.raise_for_status()
        return response.json()

async def get_user_by_id(user_id: str) -> dict | None:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{DISCORD_API}/users/{user_id}",
            headers=bot_headers(),
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()

async def get_guild(guild_id: str) -> dict | None:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{DISCORD_API}/guilds/{guild_id}",
            headers=bot_headers(),
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()

async def get_member(guild_id: str, user_id: str) -> dict | None:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{DISCORD_API}/guilds/{guild_id}/members/{user_id}",
            headers=bot_headers(),
        )
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()

async def search_members(guild_id: str, query: str, limit: int = 25) -> list:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{DISCORD_API}/guilds/{guild_id}/members/search",
            headers=bot_headers(),
            params={"query": query, "limit": limit},
        )
        response.raise_for_status()
        return response.json()

async def list_members(guild_id: str, limit: int = 100, after: str | None = None) -> list:
    params = {"limit": limit}
    if after:
        params["after"] = after

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{DISCORD_API}/guilds/{guild_id}/members",
            headers=bot_headers(),
            params=params,
        )
        response.raise_for_status()
        return response.json()

async def get_roles(guild_id: str) -> list:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{DISCORD_API}/guilds/{guild_id}/roles",
            headers=bot_headers(),
        )
        response.raise_for_status()
        return response.json()

async def add_role(guild_id: str, user_id: str, role_id: str, reason: str | None = None) -> None:
    async with httpx.AsyncClient() as client:
        response = await client.put(
            f"{DISCORD_API}/guilds/{guild_id}/members/{user_id}/roles/{role_id}",
            headers=bot_headers(reason),
        )
        response.raise_for_status()

async def remove_role(guild_id: str, user_id: str, role_id: str, reason: str | None = None) -> None:
    async with httpx.AsyncClient() as client:
        response = await client.delete(
            f"{DISCORD_API}/guilds/{guild_id}/members/{user_id}/roles/{role_id}",
            headers=bot_headers(reason),
        )
        response.raise_for_status()

async def timeout_member(guild_id: str, user_id: str, until_iso: str | None, reason: str | None = None) -> None:
    payload = {"communication_disabled_until": until_iso}
    async with httpx.AsyncClient() as client:
        response = await client.patch(
            f"{DISCORD_API}/guilds/{guild_id}/members/{user_id}",
            headers=bot_headers(reason),
            json=payload,
        )
        response.raise_for_status()

async def kick_member(guild_id: str, user_id: str, reason: str | None = None) -> None:
    async with httpx.AsyncClient() as client:
        response = await client.delete(
            f"{DISCORD_API}/guilds/{guild_id}/members/{user_id}",
            headers=bot_headers(reason),
        )
        response.raise_for_status()

async def ban_member(guild_id: str, user_id: str, reason: str | None = None) -> None:
    async with httpx.AsyncClient() as client:
        response = await client.put(
            f"{DISCORD_API}/guilds/{guild_id}/bans/{user_id}",
            headers=bot_headers(reason),
            json={"delete_message_seconds": 0},
        )
        response.raise_for_status()
