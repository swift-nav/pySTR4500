## pySTR4500

Utilities for the STR4500 GPS/SBAS Simulator with SimPLEX over TCP.

## Development Build and Setup

Hopefully,

```bash
sudo pip install ElementTree --allow-external ElementTree --allow-unverified ElementTree
python setup.py install
```

## STR4500 Software Setup

Assuming that you have a network connection to the STR500,

```python
from pySTR4500.client import *
from pySTR4500.sims import *

# Instantate device, perfom a network connection test.
dev = STR4500("192.168.1.209")
dev.status()
dev.select_scenario("C:/filepath/to/scenario/")
dev.select_scenario(parse_sims_dictionary()[2])
dev.run_scenario()
dev.end_scenario()
dev.rewind_scenario()

# Set all channels
power = 1.0
dev.set_prn(on=True)
dev.set_power(on=True)
dev.set_power_level(level=float(power), absolute=True)

# Set channels (individually)
chan = 1
dev.chan.set_prn(on=True)
dev.chan.set_power(chan, on=True)
dev.chan.set_power_mode(chan, mode=0)
dev.chan.set_prn(chan, on=True)
dev.chan.set_power_level(chan, level=float(power), absolute=True)
dev.chan.set_power_level(chan, level=float(power), absolute=False)
```

## STR4500 Software Setup

The STR4500 is controlled by SimPLEX, a Windows program that can be
run window VirtualBox. SimPLEX can act as a server, accepting a Telnet
command dictionary over BSD sockets (hardwired to 15650).

To setup and test a VirtualBox VM network connection:

1. Setup a VirtualBox VM with Windows XP. Bridged networking is known
   to work, but you'll likely want to enable a firewall on unused
   ports.

2. In the SimPLEX, in the dropdown window `Options > Remote Command
   Settings`, check the box for `Enable Remote Input` and select
   `Enable` for BSD sockets. In the `File` menu, select `Start Remote
   Task`.

3. If you're using bridged networking, use the Windows Command Prompt
   to (i) check its IP address on the Windows guest using `ipconfig`
   and (ii) confirm that its listening on port 15650 with `netstat
   -a`.

4. `telnet <ip address> 15650` from the host or guest and send a
   `NULL` command to check for a response.

## Running tests

There are two types of tests: one using a mocked TCP echo server to
test for data payloads and integration tests requiring a conection to
a live instrument. To run the first,

```shell
py.test -q tests/
```

The second class has been tested manually, but is commented out until
I figure out how to use Python's test selectors.

## LICENSE

Copyright © 2014 Swift Navigation

API documentation:
Copyright © Spirent Communications SW Ltd
