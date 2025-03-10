from homeassistant import config_entries, core
from homeassistant.const import CONF_IP_ADDRESS, CONF_TOKEN
from homeassistant.core import HomeAssistantError, callback
from homeassistant.helpers.entity import DeviceInfo

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_HS_COLOR,
    ColorMode,
    LightEntity,
)

import dirigera
from .dirigera_lib_patch import HubX

from .const import DOMAIN
from .mocks.ikea_bulb_mock import ikea_bulb_mock

import logging
import time

logger = logging.getLogger("custom_components.dirigera_platform")

from datetime import timedelta
SCAN_INTERVAL = timedelta(seconds=3)

async def async_setup_entry(
    hass: core.HomeAssistant,
    config_entry: config_entries.ConfigEntry,
    async_add_entities,
):
    logger.debug("LIGHT Starting async_setup_entry")
    """Setup sensors from a config entry created in the integrations UI."""
    config = hass.data[DOMAIN][config_entry.entry_id]
    logger.debug(config)

    # hub = dirigera.Hub(config[CONF_TOKEN], config[CONF_IP_ADDRESS])
    hub = HubX(config[CONF_TOKEN], config[CONF_IP_ADDRESS])

    lights = []

    # If mock then start with mocks
    if config[CONF_IP_ADDRESS] == "mock":
        logger.warning("Setting up mock bulbs")
        mock_bulb1 = ikea_bulb_mock(hub, "mock_bulb1")
        mock_bulb2 = ikea_bulb_mock(hub, "mock_bulb2")
        lights = [mock_bulb1, mock_bulb2]
    else:
        hub_lights = await hass.async_add_executor_job(hub.get_lights)
        lights = [ikea_bulb(hub, light, hass) for light in hub_lights]

    logger.debug("Found {} light entities to setup...".format(len(lights)))
    async_add_entities(lights)
    logger.debug("LIGHT Complete async_setup_entry")


class ikea_bulb(LightEntity):
    def __init__(self, hub, json_data, hass: core.HomeAssistant) -> None:
        logger.debug("ikea_bulb ctor...")
        self._hub = hub
        self._json_data = json_data
        self._hass = hass
        self.set_state()
        self._lastEventTime = 0
        eventName = "dirigera_message_light"
        hass.bus.async_listen(eventName, self.handle_event)

    @callback
    def handle_event(self, event) -> None:
        if self._json_data.id != event.data["sourceDeviceId"]:
            return

        current_time = time.time() * 1000
        if current_time - self._lastEventTime > 1000:
            self.schedule_update_ha_state()
            self._lastEventTime = current_time

    def set_state(self):
        # Set Color capabilities
        color_modes = []
        can_receive = self._json_data.capabilities.can_receive
        logger.debug("Got can_receive in state")
        logger.debug(can_receive)
        hasHs = False

        for cap in can_receive:
            if cap == "lightLevel":
                color_modes.append(ColorMode.BRIGHTNESS)
            elif cap == "colorTemperature":
                color_modes.append(ColorMode.COLOR_TEMP)
            elif cap in ("colorHue", "colorSaturation"):
                if not hasHs:
                    hasHs = True
                    color_modes.append(ColorMode.HS)

        self._supported_color_modes = color_modes
        logger.debug("supported color mode set to ")
        logger.debug(self._supported_color_modes)

    @property
    def unique_id(self):
        return self._json_data.id

    @property
    def available(self):
        return self._json_data.is_reachable

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={("dirigera_platform", self._json_data.id)},
            name=self._json_data.attributes.custom_name,
            manufacturer=self._json_data.attributes.manufacturer,
            model=self._json_data.attributes.model,
            sw_version=self._json_data.attributes.firmware_version,
        )

    @property
    def name(self):
        return self._json_data.attributes.custom_name

    @property
    def brightness(self):
        return int((self._json_data.attributes.light_level / 100) * 255)

    @property
    def max_color_temp_kelvin(self):
        return self._json_data.attributes.color_temperature_min

    @property
    def min_color_temp_kelvin(self):
        return self._json_data.attributes.color_temperature_max

    @property
    def color_temp_kelvin(self):
        return self._json_data.attributes.color_temperature

    @property
    def hs_color(self):
       return (self._json_data.attributes.color_hue, self._json_data.attributes.color_saturation)

    @property
    def is_on(self):
        return self._json_data.attributes.is_on

    @property
    def supported_color_modes(self):
        return self._supported_color_modes

    def update(self):
        try:
            self._json_data = self._hub.get_light_by_id(self._json_data.id)
            self.set_state()
        except Exception as ex:
            logger.error("error encountered running update on : {}".format(self.name))
            logger.error(ex)
            raise HomeAssistantError(ex, DOMAIN, "hub_exception")

    def turn_on(self, **kwargs):
        logger.debug("light turn_on...")
        logger.debug(kwargs)

        try:
            self._json_data.set_light(True)

            if ATTR_BRIGHTNESS in kwargs:
                # brightness requested
                logger.debug("Request to set brightness...")
                brightness = int(kwargs[ATTR_BRIGHTNESS])
                logger.debug("Set brightness : {}".format(brightness))
                logger.debug("scaled brightness : {}".format(int((brightness/255)*100)))
                self._json_data.set_light_level(int((brightness/255)*100))

            if ATTR_COLOR_TEMP_KELVIN in kwargs:
                # color temp requested
                # If request is white then brightness is passed
                logger.debug("Request to set color temp...")
                ct = kwargs[ATTR_COLOR_TEMP_KELVIN]
                ct = max(self.min_color_temp_kelvin, min(ct, self.max_color_temp_kelvin))
                logger.debug("Set CT : {}".format(ct))
                self._json_data.set_color_temperature(ct)

            if ATTR_HS_COLOR in kwargs:
                logger.debug("Request to set color HS")
                hs_tuple = kwargs[ATTR_HS_COLOR]
                self._hue = hs_tuple[0]
                logger.debug("Set hue : {}".format(self._hue))
                self._saturation = hs_tuple[1]
                logger.debug("scaled saturation : {}".format(self._saturation / 255))
                self._json_data.set_light_color(self._hue, self._saturation / 255)

        except Exception as ex:
            logger.error("error encountered turning on : {}".format(self.name))
            logger.error(ex)
            raise HomeAssistantError(ex,DOMAIN,"hub_exception")

    def turn_off(self, **kwargs):
        logger.debug("light turn_off...")
        try:
            self._json_data.set_light(False)
        except Exception as ex:
            logger.error("error encountered turning off : {}".format(self.name))
            logger.error(ex)
            raise HomeAssistantError(ex,DOMAIN,"hub_exception")
