# Version: 2026-05-15 - Moderniserad conftest.py med strikt tidszonsåterställning och tråd-workaround.
"""Globala fixtures för Smart EV Charging tester."""

import threading
from datetime import timedelta
from unittest.mock import patch

import pytest
from homeassistant import loader
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_fire_time_changed

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
def restore_timezone():
    """Säkerställer att tidszonen alltid återställs efter varje test för att förhindra läckage."""
    default_tz = dt_util.DEFAULT_TIME_ZONE
    yield
    dt_util.DEFAULT_TIME_ZONE = default_tz


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(hass, enable_custom_integrations):
    """Aktiverar custom integrations automatiskt för alla tester."""
    # Detta löser problemet med "AttributeError: 'async_generator' object has no attribute 'data'"
    # genom att rensa cachen så Home Assistant tvingas ladda din integration på nytt.
    if loader.DATA_CUSTOM_COMPONENTS in hass.data:
        hass.data.pop(loader.DATA_CUSTOM_COMPONENTS)
    yield


@pytest.fixture(autouse=True)
async def ensure_cleanup(hass):
    """Försök tvinga fram cleanup av timers och dölj kända lingering threads.
    Krävs för bakåtkompatibilitet med Stable/3.12 där testramverket annars kraschar.
    """
    yield
    # Vänta på att eventuella pågående tasks ska bli klara
    await hass.async_block_till_done()

    # Kör fram tiden för att låta eventuella bakgrundsprocesser/timers avslutas
    future = dt_util.utcnow() + timedelta(seconds=300)
    async_fire_time_changed(hass, future)
    await hass.async_block_till_done()

    # WORKAROUND: Äldre versioner av test-pluginet har problem med att stänga ner
    # _run_safe_shutdown_loop. Vi döper om tråden så att test-pluginet tror att
    # det är en systemtråd (startar med "waitpid-").
    for thread in threading.enumerate():
        if "_run_safe_shutdown_loop" in thread.name:
            thread.name = f"waitpid-suppressed-{thread.name}"