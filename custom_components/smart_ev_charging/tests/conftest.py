"""Globala fixtures för Smart EV Charging tester."""
import pytest
from homeassistant import loader

@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(hass, enable_custom_integrations):
    """Aktiverar custom integrations automatiskt för alla tester."""
    # Vi säkerställer att cachen för integratonsladdaren rensas
    if loader.DATA_CUSTOM_COMPONENTS in hass.data:
        hass.data.pop(loader.DATA_CUSTOM_COMPONENTS)
    yield

@pytest.fixture
def asyncio_default_fixture_loop_scope():
    """Sätter scope för asyncio till function (löser varningsmeddelandet)."""
    return "function"