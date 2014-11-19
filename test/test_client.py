#!/usr/bin/env python
# Copyright (C) 2014 Swift Navigation Inc.
# Contact: Bhaskar Mookerji <mookerji@swiftnav.com>
#
# This source is subject to the license found in the file 'LICENSE' which must
# be be distributed together with this source. All other rights reserved.
#
# THIS CODE AND INFORMATION IS PROVIDED "AS IS" WITHOUT WARRANTY OF ANY KIND,
# EITHER EXPRESSED OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND/OR FITNESS FOR A PARTICULAR PURPOSE.

from pySTR4500.client import *
import pytest
import socket

# test_string = "<msg><status>6</status></msg>"

def test_echo():
  """
  Setup a echo test with a TCP server: do we receive the right
  TELNET commands on the server side?

  """
  with STR4500("192.168.1.169") as dev:
    dev.null()
    # <CommandResponse (status = Initialised, data = None)>
    dev.run_scenario()
    # <CommandResponse (status = Arming, data = None)>
    dev.end_scenario()
    # <CommandResponse (status = Ended, data = None)>
    dev.rewind_scenario()
    # <CommandResponse (status = Initialised, data = None)>
    dev.set_trigger(0)
    dev.set_trigger(1)
    dev.set_trigger(2)
    # <CommandResponse (status = Initialised, data = None)>
    dev.power_on(on=True, all_chans=False, chan=1)
    dev.set_power_mode(all_chans=False, mode=0)
    dev.set_power_level(all_chans=False, level=3., absolute=True)
    dev.set_prn_code(on=True, all_chans=False, chan=0)
    dev.set_prn_code(on=True, all_chans=False, chan=0)
    dev.set_no_hardware_flag(mode=False)
    dev.set_popups(mode=True)
    dev.time()
    dev.scenario_duration()

def test_integration():
  """
  Runs test with a live STR4500.
  """
  pass
