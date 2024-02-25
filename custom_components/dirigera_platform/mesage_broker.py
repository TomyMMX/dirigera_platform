import threading
import logging
from typing import Any

import json
import time

from homeassistant import core

import dirigera
from .dirigera_lib_patch import HubX

logger = logging.getLogger("custom_components.dirigera_platform")


class DirigeraMessageBroker:
    def __init__(self, ip, token, hass: core.HomeAssistant) -> None:
        self._hub = HubX(token, ip)
        self._hass = hass
        self._websocket_thread = threading.Thread(target=self.run_websocket_app)
        self._websocket_thread.start()

    def handle_event(self, ws: Any, message: str) -> None:
        # Parse the incoming message
        message_dict = json.loads(message)
        data = message_dict.get("data", {})

        handled = False
        handled = self.handle_button_event(data)
        if not handled:
            handled = self.handle_light_event(data)

    def handle_ws_error(self, ws: Any, message: str) -> None:
        logger.error(message)

    def handle_ws_close(self, ws: Any, status_code: Any, close_msg: str) -> None:
        logger.debug("WS closed...")
        logger.debug("Status code: %s, Close message: %s", status_code, close_msg)
        self.run_websocket_app()

    def run_websocket_app(self) -> None:
        self._hub.create_event_listener(
            on_message=self.handle_event,
            on_error=self.handle_ws_error,
            on_close=self.handle_ws_close,
        )

    def handle_button_event(self, data) -> None:
        # Check if triggers are present in the data
        triggers = data.get("triggers", [])

        # Filter triggers for 'controller' type
        matching_triggers = [
            trigger for trigger in triggers if trigger["type"] == "controller"
        ]

        for trigger in matching_triggers:
            pattern = trigger["trigger"]["clickPattern"]
            if data["info"]["name"].startswith("ActionPress"):
                eventName = "dirigera_message_button"

                self._hass.bus.fire(
                    eventName,
                    {
                        "sourceDeviceId": trigger["trigger"]["deviceId"],
                        "pattern": pattern,
                    },
                )

                logger.debug(
                    "Button event detected... %s", pattern
                )
                return True
        return False

    def handle_light_event(self, data) -> None:
        logger.debug("handle_light_event...")
        if "type" in data and data["type"] == "light":
            eventName = "dirigera_message_light"
            self._hass.bus.fire(
                eventName,
                {
                    "sourceDeviceId": data["id"],
                    "attributes": data["attributes"],
                },
            )
            logger.debug("Light event detected... ")
            return True
        return False
