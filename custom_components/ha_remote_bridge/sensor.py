"""Status sensor for HA Remote Bridge."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import API_BASE


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the HA Remote Bridge status entity."""
    async_add_entities([HARemoteBridgeStatus(entry)])


class HARemoteBridgeStatus(Entity):
    """Represent one configured remote bridge target."""

    _attr_has_entity_name = True
    _attr_name = None

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialize the entity."""
        self._entry = entry
        self._attr_unique_id = entry.entry_id

    @property
    def state(self) -> str:
        """Return the current state."""
        return "configured"

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        """Return useful bridge metadata."""
        return {
            "bridge_path": f"{API_BASE}/{self._entry.entry_id}/",
        }
