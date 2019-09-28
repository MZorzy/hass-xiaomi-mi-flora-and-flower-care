"""Support for monitoring plants."""
from collections import deque
from datetime import datetime, timedelta
import logging

import voluptuous as vol

from homeassistant.components import group
from homeassistant.components.recorder.util import execute, session_scope
from homeassistant.const import (
    ATTR_TEMPERATURE,
    ATTR_UNIT_OF_MEASUREMENT,
    CONF_NAME,
    CONF_SENSORS,
    STATE_OK,
    STATE_PROBLEM,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    TEMP_CELSIUS,
)
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.helpers.event import async_track_state_change

"""
    My import
"""
from . import DOMAIN

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = "plant"

READING_BATTERY = "battery"
READING_TEMPERATURE = ATTR_TEMPERATURE
READING_MOISTURE = "moisture"
READING_CONDUCTIVITY = "conductivity"
READING_BRIGHTNESS = "brightness"

ATTR_PROBLEM = "problem"
ATTR_SENSORS = "sensors"
PROBLEM_NONE = "none"
ATTR_MAX_BRIGHTNESS_HISTORY = "max_brightness"

# we're not returning only one value, we're returning a dict here. So we need
# to have a separate literal for it to avoid confusion.
ATTR_DICT_OF_UNITS_OF_MEASUREMENT = "unit_of_measurement_dict"

CONF_MIN_BATTERY_LEVEL = "min_" + READING_BATTERY
CONF_MIN_TEMPERATURE = "min_" + READING_TEMPERATURE
CONF_MAX_TEMPERATURE = "max_" + READING_TEMPERATURE
CONF_MIN_MOISTURE = "min_" + READING_MOISTURE
CONF_MAX_MOISTURE = "max_" + READING_MOISTURE
CONF_MIN_CONDUCTIVITY = "min_" + READING_CONDUCTIVITY
CONF_MAX_CONDUCTIVITY = "max_" + READING_CONDUCTIVITY
CONF_MIN_BRIGHTNESS = "min_" + READING_BRIGHTNESS
CONF_MAX_BRIGHTNESS = "max_" + READING_BRIGHTNESS
CONF_CHECK_DAYS = "check_days"

CONF_SENSOR_BATTERY_LEVEL = READING_BATTERY
CONF_SENSOR_MOISTURE = READING_MOISTURE
CONF_SENSOR_CONDUCTIVITY = READING_CONDUCTIVITY
CONF_SENSOR_TEMPERATURE = READING_TEMPERATURE
CONF_SENSOR_BRIGHTNESS = READING_BRIGHTNESS

DEFAULT_MIN_BATTERY_LEVEL = 20
DEFAULT_MIN_MOISTURE = 20
DEFAULT_MAX_MOISTURE = 60
DEFAULT_MIN_CONDUCTIVITY = 500
DEFAULT_MAX_CONDUCTIVITY = 3000
DEFAULT_CHECK_DAYS = 3

"""
    My constant
"""
ATTR_INFO = "info"
ATTR_BASIC = "basic"
ATTR_MAINTENANCE = "maintenance"
ATTR_IMAGE = "image"

CONF_PLANT_ID = "plant_id"
SERVICE_API = 'flower_service'

API_PARAMETER = "parameter"
API_PARAMETER_MIN_TEMP = "min_temp"
API_PARAMETER_MAX_TEMP = "max_temp"
API_PARAMETER_MIN_SOIL_MOIST = "min_soil_moist"
API_PARAMETER_MAX_SOIL_MOIST = "max_soil_moist"
API_PARAMETER_MIN_SOIL_EC = "min_soil_ec"
API_PARAMETER_MAX_SOIL_EC = "max_soil_ec"
API_PARAMETER_MIN_LIGHT_LUX = "min_light_lux"
API_PARAMETER_MAX_LIGHT_LUX = "max_light_lux"

ATTR_RANGES = "ranges"

SCHEMA_SENSORS = vol.Schema(
    {
        vol.Optional(CONF_SENSOR_BATTERY_LEVEL): cv.entity_id,
        vol.Optional(CONF_SENSOR_MOISTURE): cv.entity_id,
        vol.Optional(CONF_SENSOR_CONDUCTIVITY): cv.entity_id,
        vol.Optional(CONF_SENSOR_TEMPERATURE): cv.entity_id,
        vol.Optional(CONF_SENSOR_BRIGHTNESS): cv.entity_id,
    }
)

DOMAIN_PLANT = "plant"
GROUP_NAME_ALL_PLANTS = "all plants"
ENTITY_ID_ALL_PLANTS = group.ENTITY_ID_FORMAT.format("all_plants")

"""
    My schemas
"""
PLANT_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_PLANT_ID): cv.string,
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_SENSORS): vol.Schema(SCHEMA_SENSORS),
    }
)

PLATFORM_SCHEMA = vol.Schema({DOMAIN: {cv.string: PLANT_SCHEMA}}, extra=vol.ALLOW_EXTRA)


# Flag for enabling/disabling the loading of the history from the database.
# This feature is turned off right now as its tests are not 100% stable.
ENABLE_LOAD_HISTORY = False


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the Plant component."""
    _LOGGER.info("__init__ setup_platform 'sensor' start for %s.", DOMAIN)

    params = {CONF_SENSORS: config.get(CONF_SENSORS)}
    app_token = hass.data[DOMAIN][SERVICE_API]

    if not (app_token is None):
        flower_info = app_token.retrieve_flower_details(config.get(CONF_PLANT_ID))
        _LOGGER.debug("__init__ setup_platform 'sensor' start for %s. Flower: %s", DOMAIN, flower_info)

        if not (params[CONF_SENSORS] is None):
            params[ATTR_RANGES] = flower_info[API_PARAMETER] ;
            params[CONF_MIN_TEMPERATURE] = flower_info[API_PARAMETER][API_PARAMETER_MIN_TEMP]
            params[CONF_MAX_TEMPERATURE] = flower_info[API_PARAMETER][API_PARAMETER_MAX_TEMP]
            params[CONF_MIN_MOISTURE] = flower_info[API_PARAMETER][API_PARAMETER_MIN_SOIL_MOIST]
            params[CONF_MAX_MOISTURE] = flower_info[API_PARAMETER][API_PARAMETER_MAX_SOIL_MOIST]
            params[CONF_MIN_CONDUCTIVITY] = flower_info[API_PARAMETER][API_PARAMETER_MIN_SOIL_EC]
            params[CONF_MAX_CONDUCTIVITY] = flower_info[API_PARAMETER][API_PARAMETER_MAX_SOIL_EC]
            params[CONF_MIN_BRIGHTNESS] = flower_info[API_PARAMETER][API_PARAMETER_MIN_LIGHT_LUX]
            params[CONF_MAX_BRIGHTNESS] = flower_info[API_PARAMETER][API_PARAMETER_MAX_LIGHT_LUX]

            params[ATTR_BASIC] = flower_info[ATTR_BASIC]
            params[ATTR_MAINTENANCE] = flower_info[ATTR_MAINTENANCE]
            params[ATTR_IMAGE] = flower_info[ATTR_IMAGE]

    if not (params[CONF_SENSORS] is None):
        component = EntityComponent(_LOGGER, DOMAIN_PLANT, hass, group_name=GROUP_NAME_ALL_PLANTS)

        entities = []

        name = config.get(CONF_NAME)
        entity = Plant(name, params)
        entities.append(entity)

        component.add_entities(entities)

    _LOGGER.info("__init__ setup_platform 'sensor' done for %s.", DOMAIN)
    return True


class Plant(Entity):
    """Plant monitors the well-being of a plant.

    It also checks the measurements against
    configurable min and max values.
    """

    READINGS = {
        READING_BATTERY: {ATTR_UNIT_OF_MEASUREMENT: "%", "min": CONF_MIN_BATTERY_LEVEL},
        READING_TEMPERATURE: {
            ATTR_UNIT_OF_MEASUREMENT: TEMP_CELSIUS,
            "min": CONF_MIN_TEMPERATURE,
            "max": CONF_MAX_TEMPERATURE,
        },
        READING_MOISTURE: {
            ATTR_UNIT_OF_MEASUREMENT: "%",
            "min": CONF_MIN_MOISTURE,
            "max": CONF_MAX_MOISTURE,
        },
        READING_CONDUCTIVITY: {
            ATTR_UNIT_OF_MEASUREMENT: "µS/cm",
            "min": CONF_MIN_CONDUCTIVITY,
            "max": CONF_MAX_CONDUCTIVITY,
        },
        READING_BRIGHTNESS: {
            ATTR_UNIT_OF_MEASUREMENT: "lux",
            "min": CONF_MIN_BRIGHTNESS,
            "max": CONF_MAX_BRIGHTNESS,
        },
    }

    def __init__(self, name, config):
        """Initialize the Plant component."""
        self._config = config
        self._sensormap = dict()
        self._readingmap = dict()
        self._unit_of_measurement = dict()
        for reading, entity_id in config["sensors"].items():
            self._sensormap[entity_id] = reading
            self._readingmap[reading] = entity_id
        self._state = None
        self._name = name
        self._battery = None
        self._moisture = None
        self._conductivity = None
        self._temperature = None
        self._brightness = None
        self._problems = PROBLEM_NONE

        self._conf_check_days = 3  # default check interval: 3 days
        if CONF_CHECK_DAYS in self._config:
            self._conf_check_days = self._config[CONF_CHECK_DAYS]
        self._brightness_history = DailyHistory(self._conf_check_days)

    @callback
    def state_changed(self, entity_id, _, new_state):
        """Update the sensor status.

        This callback is triggered, when the sensor state changes.
        """
        value = new_state.state
        _LOGGER.debug("Received callback from %s with value %s", entity_id, value)
        if value == STATE_UNKNOWN:
            return

        reading = self._sensormap[entity_id]
        if reading == READING_MOISTURE:
            if value != STATE_UNAVAILABLE:
                value = int(float(value))
            self._moisture = value
        elif reading == READING_BATTERY:
            if value != STATE_UNAVAILABLE:
                value = int(float(value))
            self._battery = value
        elif reading == READING_TEMPERATURE:
            if value != STATE_UNAVAILABLE:
                value = float(value)
            self._temperature = value
        elif reading == READING_CONDUCTIVITY:
            if value != STATE_UNAVAILABLE:
                value = int(float(value))
            self._conductivity = value
        elif reading == READING_BRIGHTNESS:
            if value != STATE_UNAVAILABLE:
                value = int(float(value))
            self._brightness = value
            self._brightness_history.add_measurement(
                self._brightness, new_state.last_updated
            )
        else:
            raise HomeAssistantError(
                f"Unknown reading from sensor {entity_id}: {value}"
            )
        if ATTR_UNIT_OF_MEASUREMENT in new_state.attributes:
            self._unit_of_measurement[reading] = new_state.attributes.get(
                ATTR_UNIT_OF_MEASUREMENT
            )
        self._update_state()

    def _update_state(self):
        """Update the state of the class based sensor data."""
        result = []
        for sensor_name in self._sensormap.values():
            params = self.READINGS[sensor_name]
            value = getattr(self, f"_{sensor_name}")
            if value is not None:
                if value == STATE_UNAVAILABLE:
                    result.append(f"{sensor_name} unavailable")
                else:
                    if sensor_name == READING_BRIGHTNESS:
                        result.append(
                            self._check_min(
                                sensor_name, self._brightness_history.max, params
                            )
                        )
                    else:
                        result.append(self._check_min(sensor_name, value, params))
                    result.append(self._check_max(sensor_name, value, params))

        result = [r for r in result if r is not None]

        if result:
            self._state = STATE_PROBLEM
            self._problems = ", ".join(result)
        else:
            self._state = STATE_OK
            self._problems = PROBLEM_NONE
        _LOGGER.debug("New data processed")
        self.async_schedule_update_ha_state()

    def _check_min(self, sensor_name, value, params):
        """If configured, check the value against the defined minimum value."""
        if "min" in params and params["min"] in self._config:
            min_value = self._config[params["min"]]
            if value < min_value:
                return f"{sensor_name} low"

    def _check_max(self, sensor_name, value, params):
        """If configured, check the value against the defined maximum value."""
        if "max" in params and params["max"] in self._config:
            max_value = self._config[params["max"]]
            if value > max_value:
                return f"{sensor_name} high"
        return None

    async def async_added_to_hass(self):
        """After being added to hass, load from history."""
        if ENABLE_LOAD_HISTORY and "recorder" in self.hass.config.components:
            # only use the database if it's configured
            self.hass.async_add_job(self._load_history_from_db)

        async_track_state_change(self.hass, list(self._sensormap), self.state_changed)

        for entity_id in self._sensormap:
            state = self.hass.states.get(entity_id)
            if state is not None:
                self.state_changed(entity_id, None, state)

    async def _load_history_from_db(self):
        """Load the history of the brightness values from the database.

        This only needs to be done once during startup.
        """
        from homeassistant.components.recorder.models import States

        start_date = datetime.now() - timedelta(days=self._conf_check_days)
        entity_id = self._readingmap.get(READING_BRIGHTNESS)
        if entity_id is None:
            _LOGGER.debug(
                "Not reading the history from the database as "
                "there is no brightness sensor configured"
            )
            return

        _LOGGER.debug("Initializing values for %s from the database", self._name)
        with session_scope(hass=self.hass) as session:
            query = (
                session.query(States)
                    .filter(
                    (States.entity_id == entity_id.lower())
                    and (States.last_updated > start_date)
                )
                    .order_by(States.last_updated.asc())
            )
            states = execute(query)

            for state in states:
                # filter out all None, NaN and "unknown" states
                # only keep real values
                try:
                    self._brightness_history.add_measurement(
                        int(state.state), state.last_updated
                    )
                except ValueError:
                    pass
        _LOGGER.debug("Initializing from database completed")
        self.async_schedule_update_ha_state()

    @property
    def should_poll(self):
        """No polling needed."""
        return False

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the entity."""
        return self._state

    @property
    def state_attributes(self):
        """Return the attributes of the entity.

        Provide the individual measurements from the
        sensor in the attributes of the device.
        """
        attrib = {
            ATTR_PROBLEM: self._problems,
            ATTR_SENSORS: self._readingmap,
            ATTR_DICT_OF_UNITS_OF_MEASUREMENT: self._unit_of_measurement,
            ATTR_INFO: self._config[ATTR_BASIC],
            ATTR_MAINTENANCE: self._config[ATTR_MAINTENANCE],
            ATTR_RANGES: self._config[ATTR_RANGES],
            ATTR_IMAGE: self._config[ATTR_IMAGE],
        }

        for reading in self._sensormap.values():
            attrib[reading] = getattr(self, f"_{reading}")

        if self._brightness_history.max is not None:
            attrib[ATTR_MAX_BRIGHTNESS_HISTORY] = self._brightness_history.max

        return attrib


class DailyHistory:
    """Stores one measurement per day for a maximum number of days.

    At the moment only the maximum value per day is kept.
    """

    def __init__(self, max_length):
        """Create new DailyHistory with a maximum length of the history."""
        self.max_length = max_length
        self._days = None
        self._max_dict = dict()
        self.max = None

    def add_measurement(self, value, timestamp=None):
        """Add a new measurement for a certain day."""
        day = (timestamp or datetime.now()).date()
        if not isinstance(value, (int, float)):
            return
        if self._days is None:
            self._days = deque()
            self._add_day(day, value)
        else:
            current_day = self._days[-1]
            if day == current_day:
                self._max_dict[day] = max(value, self._max_dict[day])
            elif day > current_day:
                self._add_day(day, value)
            else:
                _LOGGER.warning("Received old measurement, not storing it")

        self.max = max(self._max_dict.values())

    def _add_day(self, day, value):
        """Add a new day to the history.

        Deletes the oldest day, if the queue becomes too long.
        """
        if len(self._days) == self.max_length:
            oldest = self._days.popleft()
            del self._max_dict[oldest]
        self._days.append(day)
        if not isinstance(value, (int, float)):
            return
        self._max_dict[day] = value
