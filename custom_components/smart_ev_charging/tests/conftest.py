"""Globala fixtures för Smart EV Charging tester."""
import pytest
from homeassistant import loader

@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(hass, enable_custom_integrations):
    """Aktiverar custom integrations automatiskt för alla tester."""
    # Detta löser problemet med "AttributeError: 'async_generator' object has no attribute 'data'"
    # genom att rensa cachen så Home Assistant tvingas ladda din integration på nytt.
    if loader.DATA_CUSTOM_COMPONENTS in hass.data:
        hass.data.pop(loader.DATA_CUSTOM_COMPONENTS)
    yield