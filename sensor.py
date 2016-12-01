"""
Module containing the Sensor class for managing remote sensor data
"""
try:
    import collectd
except ImportError:
    import dummy_collectd as collectd
import pprint


class Sensor(object):
    """
    Represents a single sensor capable of making multiple measurements,
    e.g. temperature and battery voltage
    """
    def __init__(self, sensor_id, sensor_type, name, location,
                 measurements=None):
        """
        Initializes a sensor configuration.

        Args:
        sensor_id (int): Unique ID representing one sensor
        sensor_type (str): What kind of sensor this is
        name (str): The name of the sensor
        location (str): Description of where the sensor is
        measurements (list of Measurement): The list of kinds of measurements
            this sensor is capable of making
        """
        self.sensor_id = sensor_id
        self.sensor_type = sensor_type
        self.name = name
        self.location = location
        if measurements is None:
            measurements = {}
        self.measurements = measurements
        for measurement in self.measurements.itervalues():
            measurement.sensor = self

    def record_value(self, prefix, value):
        """
        Records a measurement value coming in from a sensor
        """
        try:
            measurement = self.measurements[prefix]
        except KeyError:
            collectd.warning("Ignoring value for unknown measurement "
                             "{}".format(prefix))
        measurement.record_value(value)

    def __str__(self):
        return "<Sensor {0!r} ID {1} {2}>".format(
            self.name, self.sensor_id, pprint.pformat(self.measurements))

    __repr__ = __str__
