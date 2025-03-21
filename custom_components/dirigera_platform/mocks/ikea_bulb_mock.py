from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_HS_COLOR,
    ColorMode,
    LightEntity
)
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity import DeviceInfo

import logging
logger = logging.getLogger("custom_components.dirigera_platform")
 
class ikea_bulb_mock(LightEntity):
    counter = 0
    def __init__(self, hub, hub_light) -> None:
        logger.debug("ikea_bulb mock ctor...")
        self._hub = hub 
        ikea_bulb_mock.counter = ikea_bulb_mock.counter + 1
        
        self._manufacturer = "IKEA of Sweden"
        self._unique_id = "L1907151129080101_" + str(ikea_bulb_mock.counter)
        self._model = "mock bulb"
        self._sw_version = "mock sw"
        self._name = "mock"

        self._name = "Mock Light {}".format(ikea_bulb_mock.counter)
        self._supported_color_modes = [ColorMode.BRIGHTNESS,ColorMode.COLOR_TEMP, ColorMode.HS]
        self._color_temp = 3000
        self._min_color_temp = 2202
        self._max_color_temp = 4000
        self._hue = 0.0
        self._saturation = 0.0
        self._brightness = 100
        self._is_on = False 
    
    @property
    def unique_id(self):
        return self._unique_id
     
    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={("dirigera_platform",self._unique_id)},
            name = self._name,
            manufacturer = self._manufacturer,
            model=self._model,
            sw_version=self._sw_version
        )
    
    def set_state(self):
        pass

    @property
    def name(self) -> str:
        return self._name

    @property
    def brightness(self):
        return int((self._brightness/100)*255)

    @property
    def max_color_temp_kelvin(self):
        return self._max_color_temp
    
    @property
    def min_color_temp_kelvin(self):
        return self._min_color_temp
    
    @property
    def color_temp_kevin(self):
        return self._color_temp
    
    @property
    def hs_color(self):
        return (self._hue, self._saturation)
    
    @property
    def is_on(self):
        return self._is_on

    @property
    def supported_color_modes(self):
        return self._supported_color_modes

    def update(self):
        logger.debug("mock update for {}...".format(self._name))
        pass

    def turn_on(self, **kwargs):
        logger.debug("turn_on...")
        logger.debug(kwargs)

        logger.debug("Request to turn on...")
        self._is_on=True
        logger.debug(kwargs)
        if ATTR_BRIGHTNESS in kwargs:
            # brightness requested
            logger.debug("Request to set brightness...")
            brightness = int(kwargs[ATTR_BRIGHTNESS]) 
            logger.debug("Set brightness : {}".format(brightness))
            self._brightness=int((brightness/255)*100)

        if ATTR_COLOR_TEMP_KELVIN in kwargs:
            # color temp requested
            # If request is white then brightness is passed
            logger.debug("Request to set color temp...")
            ct = kwargs[ATTR_COLOR_TEMP_KELVIN]
            logger.debug("Set CT : {}".format(ct))
            self._color_temp=ct
        
        if ATTR_HS_COLOR in kwargs:
            logger.debug("Request to set color HS")
            hs_tuple = kwargs[ATTR_HS_COLOR]
            self._hue = hs_tuple[0]
            self._saturation = hs_tuple[1]

    def turn_off(self, **kwargs):
        logger.debug("turn_off...")
        self._is_on = False 