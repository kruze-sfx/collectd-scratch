"""
Module containing the Measurement class for managing a single type of
measurement on a sensor
"""
try:
    import collectd
except ImportError:
    import dummy_collectd as collectd
import collections
import Queue
import time

import constants

Datapoint = collections.namedtuple(
    'Datapoint', ['metric', 'value', 'timestamp', 'dimensions',
                  'metric_type'])


class Measurement(object):
    """
    Represents a single measurement that can be made on a sensor.
    e.g. temperature.
    """
    def __init__(self, name, prefix, calibration=None, units=None,
                 metric_type=None):
        """
        Initializes a measurement configuration.

        Args:
        name (str): The name of the measurement, e.g. 'temperature'
        prefix (str): The string coming from the sensor that identifies
            the kind of measurement, e.g. 'BATT' for battery voltage
        sensor (Sensor): The sensor object to which this measurement belongs
        calibration (float): A number that will be added to the value from the
            sensor to offset any errors it may have
        units (str): The units of the measurement, e.g. 'C' for Celsius
        """
        if calibration is None:
            calibration = 0.0
        if metric_type is None:
            metric_type = constants.GAUGE
        self.name = name
        self.prefix = prefix
        self.sensor = None  # Set by the sensor's __init__()
        self.calibration = calibration
        self.units = units
        self.metric_type = metric_type
        if units:
            self.metric = '.'.join((self.name, self.units))
        else:
            self.metric = self.name
        self.metric = "{}.{}".format(self.name, self.units)
        self.queue = Queue.Queue()

    @property
    def dimensions(self):
        if self.sensor is None:
            raise ValueError("Measurement {} has no parent sensor".format(
                             self))
        return {
            'device': self.sensor.name,
            'location': self.sensor.location,
            'prefix': self.prefix,
            'sensor_id': str(self.sensor.sensor_id)
        }

    def record_value(self, value):
        """
        Records a value for a measurement, for later reading during the next
        collectd interval.

        Args:
        value (float): The value of the measurement on the sensor
        """
        value += self.calibration
        value = round(value, 3)
        timestamp = time.time()
        dp = Datapoint(self.metric, value, timestamp, self.dimensions,
                       self.metric_type)
        collectd.debug("Adding to queue: {}".format(dp))
        self.queue.put(dp)

    def __str__(self):
        return "<Measurement {0!r}({1!r})>".format(self.name, self.prefix)

    __repr__ = __str__
