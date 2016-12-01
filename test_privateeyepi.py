#!/usr/bin/env python
"""
Unit tests for the plugin, meant to be executed by pytest.
"""
import collections
import logging
import mock
import os
import pytest
import random
import serial
import StringIO
import sys
import threading
import time

import privateeyepi

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG,
                    format='%(asctime)s %(message)s')

ConfigOption = collections.namedtuple(
    'ConfigOption', ['key', 'values', 'children'])

sensor_1 = (
    ConfigOption('Id', (21,), ()),
    ConfigOption('Type', ('rf22',), ()),
    ConfigOption('Location', ('inside',), ()),
    ConfigOption('Measurement', ('temperature',), (
        ConfigOption('Prefix', ('TMPA',), ()),
        ConfigOption('Calibration', (18.3,), ()),
        ConfigOption('Units', ('deg_c',), ()))),
    ConfigOption('Measurement', ('battery',), (
        ConfigOption('Prefix', ('BATT',), ()),
        ConfigOption('Units', ('volts',), ()))),
)

sensor_2 = (
    ConfigOption('Id', (22,), ()),
    ConfigOption('Type', ('rf22',), ()),
    ConfigOption('Location', ('outside',), ()),
    ConfigOption('Measurement', ('temperature',), (
        ConfigOption('Prefix', ('TMPA',), ()),
        ConfigOption('Calibration', (2.3,), ()),
        ConfigOption('Units', ('deg_c',), ()))),
    ConfigOption('Measurement', ('battery',), (
        ConfigOption('Prefix', ('BATT',), ()),
        ConfigOption('Units', ('volts',), ()))),
)

messages = [
    'a21AWAKE----',
    'a21BATT3.04-',
    'a21SLEEPING-',
    'a22TMPA-1.35',
    'a99TMPA2.032',  # Should cause a warning message
    'a21TMPA0.021',
    'a22AWAKE----',
    'a22BATT3.04-',
    'a22SLEEPING-',
    'a21TMPA-1.35',
    'a22TMPA0.021',
]


class MockSerial(threading.Thread):
    def __init__(self, *args, **kwargs):
        threading.Thread.__init__(self, *args, **kwargs)
        self.daemon = True
        self.buf = StringIO.StringIO()
        self.buf_read_cursor = 0
        self.lock = threading.Lock()

    def __call__(self, *args, **kwargs):
        return self

    def run(self):
        for message in messages:
            delay = random.randint(5, 15)
            time.sleep(delay)
            with self.lock:
                logging.debug("Mock sensor message: {}".format(message))
                self.buf.write(message)

    def read(self, num):
        with self.lock:
            self.buf.seek(self.buf_read_cursor, os.SEEK_SET)
            chars = self.buf.read(num)
            self.buf_read_cursor = self.buf.tell()
            self.buf.seek(0, os.SEEK_END)
            return chars

    @property
    def in_waiting(self):
        with self.lock:
            return self.buf_read_cursor < self.buf.len


@pytest.fixture(scope="session")
def mock_serial():
    serial_obj = MockSerial()
    serial_obj.start()
    return serial_obj


@pytest.fixture(scope="session")
def mock_config():
    mock_config = mock.Mock()
    mock_config.children = [
        ConfigOption('Sensor', ('inside_thermometer',), sensor_1),
        ConfigOption('Sensor', ('outside_thermometer',), sensor_2),
    ]
    return mock_config


@pytest.fixture(scope='function', autouse=True)
def patch(monkeypatch, mock_serial):
    monkeypatch.setattr(serial, 'Serial', mock_serial)


def test_start_plugin(mock_config):
    DURATION = 120  # seconds
    INTERVAL = 10  # seconds
    privateeyepi.collectd.INSTANCE.init_logging()
    privateeyepi.collectd.INSTANCE.engine_run_config(mock_config)
    privateeyepi.collectd.INSTANCE.engine_run_init()

    start = time.time()
    next_poll = start
    end = start + DURATION
    privateeyepi.collectd.INSTANCE.engine_read_metrics()
    while time.time() < end:
        next_poll += INTERVAL
        time.sleep(next_poll - time.time())
        privateeyepi.collectd.INSTANCE.engine_read_metrics()

    privateeyepi.collectd.INSTANCE.engine_read_metrics()
    privateeyepi.collectd.INSTANCE.engine_run_shutdowns()
