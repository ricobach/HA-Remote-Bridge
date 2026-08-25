"""Constants for HA Remote Bridge."""

DOMAIN = "ha_remote_bridge"

CONF_RESOURCE_NAME = "resource_name"
CONF_VERIFY_SSL = "verify_ssl"
CONF_RESOURCE_TYPE = "resource_type"
CONF_SOURCE_ENTRY_ID = "source_entry_id"
CONF_ESPHOME_ENTRY_ID = "esphome_entry_id"

RESOURCE_TYPE_GENERIC = "generic"
RESOURCE_TYPE_ESPHOME = "esphome"

DEFAULT_VERIFY_SSL = True

PLATFORMS = ["sensor"]
API_BASE = "/api/ha_remote_bridge"
