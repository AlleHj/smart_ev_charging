# File version: 2025-06-05 0.2.0
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.core import HomeAssistant

from .const import (
    CONF_DEBUG_LOGGING,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL_SECONDS,
    DOMAIN,
)
from .coordinator import SmartEVChargingCoordinator

_LOGGER = logging.getLogger(__name__)
_COMPONENT_LOGGER = logging.getLogger(f"custom_components.{DOMAIN}")

PLATFORMS = ["switch", "number", "sensor"]  # Definiera vilka plattformar som ska laddas


def _update_logger_level(debug_enabled: bool) -> None:
    """Uppdaterar loggnivån för integrationsspecifika loggers."""
    if debug_enabled:
        _COMPONENT_LOGGER.setLevel(logging.DEBUG)
        _LOGGER.info("Debug-loggning aktiverad för %s.", DOMAIN)
    else:
        _COMPONENT_LOGGER.setLevel(logging.INFO)


async def async_options_update_listener(
    hass: HomeAssistant, entry: ConfigEntry
) -> None:
    """Hanterar uppdateringar av alternativ från UI."""
    _LOGGER.info(
        "Alternativ uppdaterade för %s (entry_id: %s), laddar om integrationen.",
        entry.title,
        entry.entry_id,
    )
    await hass.config_entries.async_reload(entry.entry_id)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Konfigurerar Smart EV Charging från en config entry."""
    _LOGGER.debug(
        "--- DEBUG INIT: async_setup_entry STARTAR för %s ---", entry.entry_id
    )

    current_config_for_init = {**entry.data, **entry.options}
    _LOGGER.debug(
        "--- DEBUG INIT: Använder lokal config för setup: %s ---",
        current_config_for_init,
    )

    debug_enabled = current_config_for_init.get(CONF_DEBUG_LOGGING, False)
    _update_logger_level(debug_enabled)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": None,
        "options_listener": entry.add_update_listener(async_options_update_listener),
    }
    _LOGGER.debug(
        "--- DEBUG INIT: hass.data initialiserad för entry_id %s ---", entry.entry_id
    )

    scan_interval_value = current_config_for_init.get(
        CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_SECONDS
    )
    scan_interval_seconds: int
    try:
        scan_interval_seconds = int(scan_interval_value)
        if scan_interval_seconds < 10:
            _COMPONENT_LOGGER.warning(
                "Scan interval för lågt (%s sekunder), sätter till 10 sekunder.",
                scan_interval_seconds,
            )
            scan_interval_seconds = 10
    except (ValueError, TypeError):
        _COMPONENT_LOGGER.warning(
            "Ogiltigt värde för scan_interval ('%s'), använder default %s sekunder.",
            scan_interval_value,
            DEFAULT_SCAN_INTERVAL_SECONDS,
        )
        scan_interval_seconds = DEFAULT_SCAN_INTERVAL_SECONDS

    _COMPONENT_LOGGER.debug(
        "--- DEBUG INIT: Koordinatorns scan-intervall kommer att vara: %s sekunder ---",
        scan_interval_seconds,
    )

    try:
        coordinator = SmartEVChargingCoordinator(
            hass,
            entry,
            scan_interval_seconds,
        )
        _COMPONENT_LOGGER.debug(
            "--- DEBUG INIT: SmartEVChargingCoordinator-objekt SKAPAT ---"
        )

        await coordinator.async_config_entry_first_refresh()

        hass.data[DOMAIN][entry.entry_id]["coordinator"] = coordinator
        _COMPONENT_LOGGER.debug("--- DEBUG INIT: Koordinator lagrad i hass.data ---")

    except Exception as e:
        _COMPONENT_LOGGER.error(
            "--- DEBUG INIT: FEL vid skapande eller första refresh av koordinator: %s ---",
            e,
            exc_info=True,
        )
        if entry.entry_id in hass.data[DOMAIN]:
            if listener_remover := hass.data[DOMAIN][entry.entry_id].get(
                "options_listener"
            ):
                listener_remover()
            hass.data[DOMAIN].pop(entry.entry_id)
        return False

    try:
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
        _COMPONENT_LOGGER.debug(
            "--- DEBUG INIT: async_forward_entry_setups KLAR för plattformar: %s ---",
            PLATFORMS,
        )
    except Exception as e:
        _COMPONENT_LOGGER.error(
            "--- DEBUG INIT: FEL vid async_forward_entry_setups: %s ---",
            e,
            exc_info=True,
        )
        await async_unload_entry(hass, entry)
        return False

    async def _shutdown_handler(event):
        _COMPONENT_LOGGER.debug(
            "Home Assistant stängs ner, anropar koordinatorns cleanup för %s.",
            entry.entry_id,
        )
        if coord := hass.data[DOMAIN].get(entry.entry_id, {}).get("coordinator"):
            await coord.cleanup()

    entry.async_on_unload(
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, _shutdown_handler)
    )

    _COMPONENT_LOGGER.info(
        "%s med entry_id %s är nu uppsatt och redo.", DOMAIN, entry.entry_id
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Avlastar en config entry."""
    _COMPONENT_LOGGER.info(
        "Avlastar %s med entry_id %s (Titel: %s)", DOMAIN, entry.entry_id, entry.title
    )

    entry_data = hass.data[DOMAIN].get(entry.entry_id)
    all_unloaded_ok = True

    if entry_data:
        coordinator: SmartEVChargingCoordinator | None = entry_data.get("coordinator")
        if coordinator:
            await coordinator.cleanup()
            _COMPONENT_LOGGER.debug(
                "Koordinatorns cleanup-metod anropad för %s", entry.entry_id
            )

        options_listener_remover = entry_data.get("options_listener")
        if options_listener_remover:
            options_listener_remover()
            _COMPONENT_LOGGER.debug("Options listener borttagen för %s", entry.entry_id)

        unload_results = await hass.config_entries.async_unload_platforms(
            entry, PLATFORMS
        )

        if not unload_results:
            _COMPONENT_LOGGER.warning(
                "En eller flera plattformar kunde inte avlastas korrekt för %s.",
                entry.entry_id,
            )
            all_unloaded_ok = False
        else:
            _COMPONENT_LOGGER.debug(
                "Alla plattformar (%s) avlastade korrekt för %s.",
                PLATFORMS,
                entry.entry_id,
            )

        hass.data[DOMAIN].pop(entry.entry_id, None)
    return all_unloaded_ok
