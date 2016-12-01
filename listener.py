"""
Module containing the Listener class for listening to incoming sensor messages
"""
try:
    import collectd
except ImportError:
    import dummy_collectd as collectd
import re
import serial
import threading
import time

import constants


class UnparsableMessage(ValueError):
    pass


class Listener(threading.Thread):
    """
    Background thread that listens for incoming messages on the serial
    port. If any messages are received, it determines which sensor and
    measurement it came from and places the value into a queue for
    that measurement.
    """
    # Example messages:
    # 'a21BATT3.04-'
    # 'a21SLEEPING-'
    # 'a21TMPA-1.35'
    # 'a21AWAKE----'
    # 'a21TMPA0.021'
    msg_regex = re.compile(r'(\d{2})([A-Z]{4})([+-]?\d*\.?\d+)$')

    def __init__(self, sensors):
        """
        Initialize the listener thread.

        Args:
        sensors (dict of id: Sensor): Map of sensor IDs to sensors
        """
        threading.Thread.__init__(self)
        self._sensors = sensors
        self.daemon = True
        self._stop = threading.Event()
        self._serial = serial.Serial(port=constants.SERIAL_PORT,
                                     baudrate=constants.BAUD_RATE)

    def _parse_msg(self, msg):
        """
        Parses a message from the serial port and extracts the sensor ID,
        measurement type, and value.

        Example message: '21TMPA-1.35'

        Args:
        msg(str): The incoming message
        """
        msg = msg.rstrip('-')
        m = self.msg_regex.match(msg)
        if not m:
            raise UnparsableMessage()
        sensor_id = int(m.group(1))
        measurement = str(m.group(2))
        value = float(m.group(3))
        return sensor_id, measurement, value

    def _read_message(self):
        """
        Reads a message from the serial port. Assumes that the serial
        buffer already has data in it, indicated by self._serial.in_waiting.
        """
        # Read 1 character and see if a new message is starting
        first = self._serial.read(1)
        if first != constants.MSG_START:
            collectd.debug("Not the start of an expected message: "
                           "{} != {}".format(first, constants.MSG_START))
            return
        # A new message has arrived. Parse it.
        msg = self._serial.read(11)
        try:
            sensor_id, meas_prefix, value = self._parse_msg(msg)
        except UnparsableMessage:
            collectd.warning("Ignoring message: {}".format(msg))
            return
        try:
            sensor = self._sensors[sensor_id]
        except KeyError:
            collectd.warning("Received message {} for undefined sensor "
                             "{}".format(msg, sensor_id))
            return
        collectd.info("Sensor {}: Recording value {} for measurement "
                      "{}".format(sensor_id, value, meas_prefix))
        sensor.record_value(meas_prefix, value)

    def run(self):
        collectd.info("Starting sensor listener thread")
        while not self._stop.is_set():
            while self._serial.in_waiting:
                # If in_waiting is positive, there is data ready to be read.
                self._read_message()
                time.sleep(0.2)
            time.sleep(1)


    def stop(self):
        collectd.info("Stopping sensor listener thread")
        self._stop.set()
