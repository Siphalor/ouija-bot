import asyncio
import json
import os.path
from typing import Dict, Any, Optional, List, Tuple

import interactions
from interactions.client.get import get as interactions_get

_FILE = "data/persistence.json"
_DEFAULT = {
    "running": False,
    "message": "",
    "mode": "poll",
    "unit": "letter",
    "interval": 8,
    "lowercase": True,
    "channel_id": None,
}

_persisted_data: Dict[str, Dict[str, Any]] = {}
_running_guilds: Dict[str, Dict[str, Any]] = {}


def load():
    global _persisted_data
    if os.path.exists(_FILE):
        with open(_FILE, "r") as file:
            _persisted_data = json.load(file)

            for (s_id, guild) in _persisted_data.items():
                if guild["running"]:
                    _running_guilds[s_id] = {
                        "timer": 0,
                        "guild": guild,
                        "units": {},
                        "misses": 0
                    }
    else:
        _persisted_data = {}


def save():
    global _persisted_data
    os.makedirs(os.path.dirname(_FILE), exist_ok=True)
    with open(_FILE, "w") as file:
        json.dump(_persisted_data, file)


def get_guild(s_id: str) -> Dict[str, Any]:
    if s_id not in _persisted_data:
        _persisted_data[s_id] = _DEFAULT.copy()

    return _persisted_data[s_id]


def stop_guild(s_id: str):
    _running_guilds.pop(s_id)
    _persisted_data[s_id]["running"] = False


def start_guild(s_id: str, channel: interactions.Channel):
    guild_data = get_guild(s_id)
    guild_data["running"] = True
    guild_data["message"] = ""
    guild_data["channel_id"] = str(channel.id)
    _running_guilds[s_id] = {
        "timer": 0,
        "channel": channel,
        "guild": guild_data,
        "units": {},
        "misses": 0
    }


async def get_running(s_id: str, client: interactions.Client) -> Optional[Dict[str, Any]]:
    if s_id in _running_guilds:
        return await resolve_running(_running_guilds[s_id], client)

    return None


async def resolve_running(data: Dict[str, Any], client: interactions.Client) -> Dict[str, Any]:
    if 'channel' not in data:
        data['channel'] = await interactions_get(
            client, interactions.Channel, object_id=data['guild']['channel_id']
        )
    return data


async def get_all_running(client: interactions.Client) -> List[Dict[str, Any]]:
    # noinspection PyTypeChecker
    return await asyncio.gather(*[
        resolve_running(data, client) for data in _running_guilds.values()
    ])

