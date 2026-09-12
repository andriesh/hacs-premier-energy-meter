from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([PremierEnergyMeterReading(entry)])


class PremierEnergyMeterReading(NumberEntity):
    _attr_has_entity_name = True
    _attr_icon = "mdi:counter"
    _attr_mode = NumberMode.BOX
    _attr_name = "Meter reading"
    _attr_native_max_value = 9_999_999_999
    _attr_native_min_value = 0
    _attr_native_step = 1

    def __init__(self, entry: ConfigEntry) -> None:
        self._attr_unique_id = f"{entry.entry_id}_meter_reading"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": entry.title,
        }
        self._attr_native_value = 0

    async def async_set_native_value(self, value: float) -> None:
        self._attr_native_value = value
        self.async_write_ha_state()