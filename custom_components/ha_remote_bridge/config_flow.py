"""Config flow for HA Remote Bridge."""

from __future__ import annotations

from urllib.parse import urlparse

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_URL

from .const import (
    CONF_ESPHOME_ENTRY_ID,
    CONF_RESOURCE_NAME,
    CONF_RESOURCE_TYPE,
    CONF_SOURCE_ENTRY_ID,
    CONF_VERIFY_SSL,
    DEFAULT_VERIFY_SSL,
    DOMAIN,
    RESOURCE_TYPE_ESPHOME,
    RESOURCE_TYPE_GENERIC,
)

_ESPHOME_DOMAIN = "esphome"


def _http_url_for_host(host: str) -> str:
    """Build an HTTP URL for a hostname or literal IPv6 address."""
    normalized = host.strip().rstrip(".")
    if ":" in normalized and not normalized.startswith("["):
        normalized = f"[{normalized}]"
    return f"http://{normalized}"


class HARemoteBridgeConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for HA Remote Bridge."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict | None = None
    ) -> ConfigFlowResult:
        """Choose whether to import ESPHome or configure a resource manually."""
        return self.async_show_menu(
            step_id="user",
            menu_options=["esphome", "manual"],
        )

    def _esphome_candidates(self) -> dict[str, ConfigEntry]:
        """Return ESPHome entries that expose a host and are not already imported."""
        bridge_entries = self.hass.config_entries.async_entries(DOMAIN)
        imported_entry_ids = {
            entry.data.get(CONF_SOURCE_ENTRY_ID)
            for entry in bridge_entries
            if entry.data.get(CONF_RESOURCE_TYPE) == RESOURCE_TYPE_ESPHOME
        }
        configured_urls = {
            str(entry.data.get(CONF_URL, "")).strip().rstrip("/").lower()
            for entry in bridge_entries
            if entry.data.get(CONF_URL)
        }

        candidates: dict[str, ConfigEntry] = {}
        for entry in self.hass.config_entries.async_entries(_ESPHOME_DOMAIN):
            host = entry.data.get(CONF_HOST)
            if not host or entry.entry_id in imported_entry_ids:
                continue
            if _http_url_for_host(str(host)).lower() in configured_urls:
                continue
            candidates[entry.entry_id] = entry

        return candidates

    async def async_step_esphome(
        self, user_input: dict | None = None
    ) -> ConfigFlowResult:
        """Import a device already configured by Home Assistant's ESPHome integration."""
        candidates = self._esphome_candidates()
        if not candidates:
            return self.async_abort(reason="no_esphome_devices")

        if user_input is not None:
            esphome_entry = candidates.get(user_input[CONF_ESPHOME_ENTRY_ID])
            if esphome_entry is None:
                return self.async_abort(reason="esphome_device_unavailable")

            host = str(esphome_entry.data[CONF_HOST])
            url = _http_url_for_host(host)
            unique_source = esphome_entry.unique_id or esphome_entry.entry_id

            await self.async_set_unique_id(f"esphome:{unique_source}")
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=esphome_entry.title,
                data={
                    CONF_RESOURCE_NAME: esphome_entry.title,
                    CONF_URL: url,
                    CONF_VERIFY_SSL: False,
                    CONF_RESOURCE_TYPE: RESOURCE_TYPE_ESPHOME,
                    CONF_SOURCE_ENTRY_ID: esphome_entry.entry_id,
                },
            )

        choices = {
            entry_id: f"{entry.title} — {entry.data[CONF_HOST]}"
            for entry_id, entry in sorted(
                candidates.items(),
                key=lambda item: item[1].title.casefold(),
            )
        }

        return self.async_show_form(
            step_id="esphome",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ESPHOME_ENTRY_ID): vol.In(choices),
                }
            ),
        )

    async def async_step_manual(
        self, user_input: dict | None = None
    ) -> ConfigFlowResult:
        """Configure a local HTTP or HTTPS resource manually."""
        errors: dict[str, str] = {}

        if user_input is not None:
            resource_name = user_input[CONF_RESOURCE_NAME].strip()
            url = user_input[CONF_URL].strip().rstrip("/")
            parsed = urlparse(url)

            if parsed.scheme not in {"http", "https"} or not parsed.hostname:
                errors[CONF_URL] = "invalid_url"
            else:
                await self.async_set_unique_id(url.lower())
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=resource_name,
                    data={
                        CONF_RESOURCE_NAME: resource_name,
                        CONF_URL: url,
                        CONF_VERIFY_SSL: user_input[CONF_VERIFY_SSL],
                        CONF_RESOURCE_TYPE: RESOURCE_TYPE_GENERIC,
                    },
                )

        return self.async_show_form(
            step_id="manual",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_RESOURCE_NAME): str,
                    vol.Required(CONF_URL): str,
                    vol.Optional(
                        CONF_VERIFY_SSL, default=DEFAULT_VERIFY_SSL
                    ): bool,
                }
            ),
            errors=errors,
        )
