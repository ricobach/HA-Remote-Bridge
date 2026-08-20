"""Config flow for HA Remote Bridge."""

from __future__ import annotations

from urllib.parse import urlparse

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME, CONF_URL
from homeassistant.data_entry_flow import FlowResult

from .const import CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL, DOMAIN


class HARemoteBridgeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for HA Remote Bridge."""

    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        """Configure a local HTTP or HTTPS resource."""
        errors: dict[str, str] = {}

        if user_input is not None:
            url = user_input[CONF_URL].strip().rstrip("/")
            parsed = urlparse(url)

            if parsed.scheme not in {"http", "https"} or not parsed.hostname:
                errors[CONF_URL] = "invalid_url"
            else:
                await self.async_set_unique_id(url.lower())
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=user_input[CONF_NAME].strip(),
                    data={
                        CONF_NAME: user_input[CONF_NAME].strip(),
                        CONF_URL: url,
                        CONF_VERIFY_SSL: user_input[CONF_VERIFY_SSL],
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME): str,
                    vol.Required(CONF_URL): str,
                    vol.Optional(
                        CONF_VERIFY_SSL, default=DEFAULT_VERIFY_SSL
                    ): bool,
                }
            ),
            errors=errors,
        )
