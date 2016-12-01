"""
This is a collectd python plugin that reads sensor data from a
PrivateEyePi base station. Currently only RF thermometers are supported.
"""
try:
    import collectd
except ImportError:
    import dummy_collectd as collectd
import pprint
import Queue

import constants
import listener
import measurement
import sensor

listener_thr = None
sensors = {}


def _init_measurement(measurement_config):
    """
    Helper function that parses information about a single measurement
    configuration for a specific sensor in the configuration file.

    Args:
    measurement_config (collectd.Config): Config object from parsing
        the config file

    Returns:
        Tuple of (name prefix(str), Measurement instance)
    """
    name = measurement_config.values[0]
    prefix = None
    calibration = None
    units = None
    for val in measurement_config.children:
        if val.key == 'Prefix':
            prefix = val.values[0]
        elif val.key == 'Calibration':
            calibration = float(val.values[0])
        elif val.key == 'Units':
            units = val.values[0]
    if prefix is None:
        raise ValueError("Prefix required for measurement {}".format(name))
    m = measurement.Measurement(name, prefix, calibration=calibration,
                                units=units)
    return prefix, m


def _add_sensor(sensor_config):
    """
    Helper function that parses information about a single sensor from
    the configuration file

    Args:
    sensor_config (collectd.Config): Config object from parsing the config file
    """
    global sensors
    sensor_id = None
    sensor_type = constants.UNSPECIFIED
    location = constants.UNSPECIFIED
    name = sensor_config.values[0]
    measurements = {}
    for val in sensor_config.children:
        if val.key == 'Measurement':
            prefix, meas = _init_measurement(val)
            measurements.update({prefix: meas})
        elif val.key == 'Id':
            sensor_id = int(val.values[0])
        elif val.key == 'Type':
            sensor_type = val.values[0]
        elif val.key == 'Location':
            location = val.values[0]
    if sensor_id is None:
        raise ValueError("Must specify a sensor ID for {}".format(name))
    sensors[sensor_id] = sensor.Sensor(sensor_id, sensor_type, name, location,
                                       measurements=measurements)


def _format_signalfx_dimensions(dimensions):
    """
    Formats a dictionary of dimensions to a format that enables them to be
    specified as key, value pairs in plugin_instance to signalfx. E.g.

    >>> dimensions = {'a': 'foo', 'b': 'bar'}
    >>> _format_signalfx_dimensions(dimensions)
    "[a=foo,b=bar]"

    Args:
    dimensions (dict): Mapping of {dimension_name: value, ...}

    Returns:
    str: Comma-separated list of dimensions
    """
    dim_pairs = ("{}={}".format(k, v) for k, v in dimensions.iteritems())
    dim_str = ",".join(dim_pairs)
    dim_str = "[{}]".format(dim_str)
    return dim_str


def _post_datapoint(datapoint):
    """
    Posts datapoints to collectd.

    Args:
    datapoint (namedtuple): tuple of (metric, value, timestamp,
        dimensions, metric_type)
    """
    output = collectd.Values()
    output.type = datapoint.metric_type
    output.type_instance = datapoint.metric
    output.plugin = constants.PLUGIN_NAME
    output.plugin_instance = _format_signalfx_dimensions(datapoint.dimensions)
    output.time = datapoint.timestamp
    output.values = (datapoint.value,)
    pprint_dict = {
        'plugin': output.plugin,
        'plugin_instance': output.plugin_instance,
        'time': output.time,
        'type': output.type,
        'type_instance': output.type_instance,
        'values': output.values
    }
    collectd.info(pprint.pformat(pprint_dict))
    output.dispatch()


def config(config_values):
    """
    Loads information from the plugin config file.

    Args:
    config_values (collectd.Config): Object containing config values
    """
    for val in config_values.children:
        if val.key == 'Sensor':
            _add_sensor(val)


def init():
    """
    Initializes the plugin. Starts a background thread that listens for
    new readings from sensors.
    """
    global listener_thr
    collectd.info("Initializing PrivateEyePi plugin")
    listener_thr = listener.Listener(sensors)
    listener_thr.start()


def read():
    """
    This function is called at regular intervals by collectd. Every time it
    is called, it checks to see if there are any new readings for each sensor.
    If there are, they are published to the collectd output plugins.
    """
    for sensor_ in sensors.itervalues():
        for measurement_ in sensor_.measurements.itervalues():
            while True:
                try:
                    dp = measurement_.queue.get(block=False)
                    _post_datapoint(dp)
                except Queue.Empty:
                    # No more datapoints received this interval
                    break


def shutdown():
    """
    Stops the listening thread and shuts down the plugin.
    """
    global listener_thr
    collectd.info("Stopping PrivateEyePi plugin")
    listener_thr.stop()
    listener_thr.join(timeout=5)
    if listener_thr.is_alive():
        raise ValueError("Listener thread killed forcefully")


def setup_collectd():
    """
    Registers callback functions with collectd
    """
    collectd.register_config(config)
    collectd.register_init(init)
    collectd.register_read(read)
    collectd.register_shutdown(shutdown)


setup_collectd()
