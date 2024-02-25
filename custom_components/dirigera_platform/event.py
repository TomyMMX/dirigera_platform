from homeassistant import config_entries, core
from homeassistant.const import CONF_IP_ADDRESS, CONF_TOKEN
from homeassistant.core import HomeAssistantError, callback
from homeassistant.helpers.entity import DeviceInfo

from homeassistant.components.event import EventEntity, EventDeviceClass

import dirigera
from .dirigera_lib_patch import HubX

from .const import DOMAIN
from typing import Any

import logging
import time

logger = logging.getLogger("custom_components.dirigera_platform")


async def async_setup_entry(
    hass: core.HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities,
):
    logger.debug("EVENT Starting async_setup_entry")
    """Setup sensors from a config entry created in the integrations UI."""
    config = hass.data[DOMAIN][config_entry.entry_id]
    logger.debug(config)

    # hub = dirigera.Hub(config[CONF_TOKEN], config[CONF_IP_ADDRESS])
    hub = HubX(config[CONF_TOKEN], config[CONF_IP_ADDRESS])

    buttons = []

    # If mock then start with mocks
    if config[CONF_IP_ADDRESS] != "mock":
        hub_buttons = await hass.async_add_executor_job(hub.get_controllers)
        hub_shortcut_buttons = [
            b for b in hub_buttons if b.device_type == "shortcutController"
        ]
        buttons = [ikea_button(hub, button, hass) for button in hub_shortcut_buttons]

    logger.debug("Found {} event entities to setup...".format(len(buttons)))
    async_add_entities(buttons)
    logger.debug("EVENT Complete async_setup_entry")


class ikea_button(EventEntity):
    _attr_event_types = ["single_press"]
    _attr_device_class = EventDeviceClass.BUTTON

    def __init__(self, hub, json_data, hass: core.HomeAssistant) -> None:
        logger.debug("ikea_button ctor...")

        self._json_data = json_data
        self._hass = hass
        self._hub = hub
        self._lastPressTime = 0

        eventName = "dirigera_message_button"
        hass.bus.async_listen(eventName, self.handle_event)

    @callback
    def handle_event(self, event) -> None:
        if self._json_data.id != event.data["sourceDeviceId"]:
            return

        current_time = time.time() * 1000
        if current_time - self._lastPressTime > 200:
            if event.data["pattern"] == "singlePress":
                self._trigger_event("single_press")
                self.async_write_ha_state()
            self._lastPressTime = current_time

    @property
    def unique_id(self):
        return self._json_data.id

    @property
    def name(self):
        return self._json_data.attributes.custom_name

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={("dirigera_platform", self._json_data.id)},
            name=self._json_data.attributes.custom_name,
            manufacturer=self._json_data.attributes.manufacturer,
            model=self._json_data.attributes.model,
            sw_version=self._json_data.attributes.firmware_version,
        )

    def update(self):
        try:
            self._json_data = self._hub.get_controller_by_id(self._json_data.id)
        except Exception as ex:
            logger.error("error encountered running update on : {}".format(self.name))
            logger.error(ex)
            raise HomeAssistantError(ex, DOMAIN, "hub_exception")
