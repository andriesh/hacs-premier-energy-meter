from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers import selector

from .const import CONF_CAMERA_ENTITY_ID, CONF_NLC, DOMAIN


class PremierEnergyMeterConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_NLC])
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=f"Premier Energy ({user_input[CONF_NLC]})",
                data=user_input,
            )

        schema = vol.Schema(
            {
                vol.Required(CONF_USERNAME): str,
                vol.Required(CONF_PASSWORD): str,
                vol.Required(CONF_NLC): str,
                vol.Required(CONF_CAMERA_ENTITY_ID): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="camera")
                ),
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)
