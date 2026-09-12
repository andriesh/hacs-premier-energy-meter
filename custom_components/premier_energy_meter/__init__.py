from __future__ import annotations

import asyncio
import base64
import logging
import re
from datetime import date
from pathlib import Path

import aiohttp
import voluptuous as vol

from homeassistant.components.camera import DOMAIN as CAMERA_DOMAIN, SERVICE_SNAPSHOT
from homeassistant.components import frontend
from homeassistant.components.lovelace.const import LOVELACE_DATA
from homeassistant.components.lovelace.dashboard import LovelaceStorage
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.storage import Store

from .const import (
    ATTR_CONFIG_ENTRY_ID,
    ATTR_READING,
    CONF_CAMERA_ENTITY_ID,
    CONF_NLC,
    DASHBOARD_ID,
    DASHBOARD_TITLE,
    DASHBOARD_URL_PATH,
    DOMAIN,
    LOGIN_URL,
    PLATFORMS,
    SERVICE_SUBMIT_READING,
    SUBMIT_URL,
)

_LOGGER = logging.getLogger(__name__)
_TOKEN_RE = re.compile(r'__RequestVerificationToken" type="hidden" value="([^"]+)"')

SERVICE_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_READING): cv.string,
        vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string,
    }
)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    hass.data.setdefault(DOMAIN, {})

    async def handle_submit(call: ServiceCall) -> None:
        entries = hass.config_entries.async_entries(DOMAIN)
        entry_id = call.data.get(ATTR_CONFIG_ENTRY_ID)
        entry = next((item for item in entries if item.entry_id == entry_id), None) if entry_id else None
        if entry is None and len(entries) == 1:
            entry = entries[0]
        if entry is None:
            raise HomeAssistantError("Specify config_entry_id when more than one Premier Energy account is configured")

        reading = call.data.get(ATTR_READING)
        if reading is None:
            reading = _get_meter_reading(hass, entry)
        reading = reading.strip()
        if not reading.isdigit():
            raise HomeAssistantError("Reading must contain digits only")

        await _async_submit_reading(hass, entry, reading)

    hass.services.async_register(DOMAIN, SERVICE_SUBMIT_READING, handle_submit, schema=SERVICE_SCHEMA)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await _async_create_dashboard(hass, entry)

    await _async_notify(
        hass,
        "Premier Energy Meter configured",
        "The meter reading entity is ready. Add the dashboard card from the integration documentation.",
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


def _get_meter_reading(hass: HomeAssistant, entry: ConfigEntry) -> str:
    entity_id = er.async_get(hass).async_get_entity_id(
        "number", DOMAIN, f"{entry.entry_id}_meter_reading"
    )
    if entity_id is None or (state := hass.states.get(entity_id)) is None:
        raise HomeAssistantError("Meter reading entity is unavailable")
    return state.state


async def _async_create_dashboard(hass: HomeAssistant, entry: ConfigEntry) -> None:
    lovelace_data = hass.data.get(LOVELACE_DATA)
    if lovelace_data is None:
        return

    number_entity_id = er.async_get(hass).async_get_entity_id(
        "number", DOMAIN, f"{entry.entry_id}_meter_reading"
    )
    if number_entity_id is None:
        _LOGGER.warning("Could not determine the meter reading entity ID for dashboard setup")
        return

    dashboard_metadata = {
        "id": DASHBOARD_ID,
        "icon": "mdi:meter-electric-outline",
        "title": DASHBOARD_TITLE,
        "url_path": DASHBOARD_URL_PATH,
        "require_admin": True,
        "show_in_sidebar": True,
        "mode": "storage",
    }
    dashboard_config = {
        "title": DASHBOARD_TITLE,
        "views": [
            {
                "title": "Meter",
                "path": "meter",
                "icon": "mdi:meter-electric-outline",
                "cards": [
                    {
                        "type": "picture",
                        "image": f"/api/brands/integration/{DOMAIN}/logo.png",
                        "alt_text": "Premier Energy",
                    },
                    {
                        "type": "picture-entity",
                        "entity": entry.data[CONF_CAMERA_ENTITY_ID],
                        "name": "Electricity meter",
                        "camera_view": "live",
                        "show_state": False,
                        "show_name": True,
                    },
                    {"type": "entities", "entities": [number_entity_id]},
                    {
                        "type": "button",
                        "name": "Submit reading",
                        "icon": "mdi:upload",
                        "tap_action": {
                            "action": "perform-action",
                            "perform_action": f"{DOMAIN}.{SERVICE_SUBMIT_READING}",
                            "data": {ATTR_CONFIG_ENTRY_ID: entry.entry_id},
                        },
                    },
                ],
            }
        ],
    }

    dashboard_store = lovelace_data.dashboards.get(DASHBOARD_URL_PATH)
    if dashboard_store is None:
        dashboard_store = LovelaceStorage(hass, dashboard_metadata)
        await dashboard_store.async_save(dashboard_config)
    else:
        existing_config = await dashboard_store.async_load(False)
        cards = existing_config.get("views", [{}])[0].get("cards", [])
        logo_url = f"/api/brands/integration/{DOMAIN}/logo.png"
        if not any(card.get("image") == logo_url for card in cards):
            cards.insert(0, dashboard_config["views"][0]["cards"][0])
            await dashboard_store.async_save(existing_config)
            _LOGGER.info("Added logo card to Lovelace dashboard /%s", DASHBOARD_URL_PATH)

    dashboards_store = Store(hass, 1, "lovelace_dashboards")
    stored_dashboards = await dashboards_store.async_load() or {"items": []}
    dashboard_index = next(
        (
            index
            for index, item in enumerate(stored_dashboards["items"])
            if item.get("id") == DASHBOARD_ID or item.get("url_path") == DASHBOARD_URL_PATH
        ),
        None,
    )
    if dashboard_index is None:
        stored_dashboards["items"].append(dashboard_metadata)
    else:
        stored_dashboards["items"][dashboard_index] = dashboard_metadata
    await dashboards_store.async_save(stored_dashboards)

    if DASHBOARD_URL_PATH in lovelace_data.dashboards:
        frontend.async_register_built_in_panel(
            hass,
            "lovelace",
            frontend_url_path=DASHBOARD_URL_PATH,
            require_admin=True,
            show_in_sidebar=True,
            sidebar_title=DASHBOARD_TITLE,
            sidebar_icon="mdi:meter-electric-outline",
            config={"mode": "storage"},
            update=True,
        )
        _LOGGER.info("Repaired Lovelace dashboard metadata for /%s", DASHBOARD_URL_PATH)
        return

    lovelace_data.dashboards[DASHBOARD_URL_PATH] = dashboard_store
    frontend.async_register_built_in_panel(
        hass,
        "lovelace",
        frontend_url_path=DASHBOARD_URL_PATH,
        require_admin=True,
        show_in_sidebar=True,
        sidebar_title=DASHBOARD_TITLE,
        sidebar_icon="mdi:meter-electric-outline",
        config={"mode": "storage"},
    )
    _LOGGER.info("Created Lovelace dashboard at /%s", DASHBOARD_URL_PATH)


async def _async_submit_reading(hass: HomeAssistant, entry: ConfigEntry, reading: str) -> None:
    snapshot_name = f"premier_energy_meter_{date.today():%Y-%m-%d}.jpg"
    snapshot_path = Path(hass.config.path("www", snapshot_name))
    camera_entity_id = entry.data[CONF_CAMERA_ENTITY_ID]

    try:
        await hass.services.async_call(
            CAMERA_DOMAIN,
            SERVICE_SNAPSHOT,
            {"entity_id": camera_entity_id, "filename": str(snapshot_path)},
            blocking=True,
        )
        await _async_post_reading(hass, entry, reading, snapshot_path)
    except (aiohttp.ClientError, HomeAssistantError, OSError, ValueError) as err:
        _LOGGER.error("Premier Energy submission failed for reading %s: %s", reading, err)
        await _async_notify(hass, "Submission failed", f"Could not submit reading {reading}: {err}")
        raise HomeAssistantError(f"Premier Energy submission failed: {err}") from err

    _LOGGER.info("Premier Energy reading %s submitted successfully", reading)
    await _async_notify(hass, "Meter reading submitted", f"Reading {reading} was submitted successfully.")


async def _async_post_reading(hass: HomeAssistant, entry: ConfigEntry, reading: str, snapshot_path: Path) -> None:
    session = async_get_clientsession(hass)
    async with session.get(LOGIN_URL, allow_redirects=True) as response:
        response.raise_for_status()
        login_page = await response.text()

    token_match = _TOKEN_RE.search(login_page)
    if token_match is None:
        raise ValueError("Premier Energy login anti-forgery token was not found")

    login_payload = {
        "__RequestVerificationToken": token_match.group(1),
        "User": entry.data[CONF_USERNAME],
        "Password": entry.data[CONF_PASSWORD],
    }
    async with session.post(LOGIN_URL, data=login_payload, allow_redirects=True) as response:
        response.raise_for_status()

    image_data = await asyncio.to_thread(snapshot_path.read_bytes)
    data_url = "data:image/jpeg;base64," + base64.b64encode(image_data).decode("ascii")
    submit_payload = {
        "f_indactiv": reading,
        "NLC": entry.data[CONF_NLC],
        "Base64": data_url,
        "file.Type": "image/jpeg",
        "file.Name": snapshot_path.name,
    }
    async with session.post(SUBMIT_URL, data=submit_payload) as response:
        response.raise_for_status()


async def _async_notify(hass: HomeAssistant, title: str, message: str) -> None:
    await hass.services.async_call(
        "persistent_notification",
        "create",
        {"title": title, "message": message, "notification_id": DOMAIN},
        blocking=False,
    )
