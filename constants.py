"""
Constants for the privateeyepi collectd plugin
"""
# The baud rate of the serial port
BAUD_RATE = 9600

# The metric types
COUNTER = 'counter'
CUMULATIVE_COUNTER = 'cumulative_counter'
GAUGE = 'gauge'

# The character that indicates the start of a new message
MSG_START = 'a'

# The name of this plugin
PLUGIN_NAME = 'privateeyepi'

# The default serial port device on the base station
SERIAL_PORT = '/dev/ttyS0'

# Generic string for an unspecified argument
UNSPECIFIED = 'unspecified'
