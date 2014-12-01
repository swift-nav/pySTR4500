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

"""
Simulation and integration tests for STR4500's command dictionary.
Aside from unit tests, also includes a test of command strings using
a test server and integration tests intended to use an actual network
connection to the STR4500.

"""

from pySTR4500.client import *
from pySTR4500.sims import *
import pytest
import SocketServer
import threading

class MockRequestHandler(SocketServer.BaseRequestHandler):
  def handle(self):
    data = self.request.recv(1024)
    response = "<msg><status>1</status><data>%s</data></msg>" % data
    self.request.sendall(response)

class MockServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
  pass

def test_response_parsing():
  """
  Test XML response parsing.
  """
  assert CommandResponse.fromstring("<msg><status>0</status></msg>") \
    == CommandResponse("No scenario specified", None)
  assert CommandResponse.fromstring("<msg><status>1</status></msg>") \
    == CommandResponse("Invalid scenario", None)
  assert CommandResponse.fromstring("<msg><status>2</status></msg>") \
    == CommandResponse("Initialised", None)
  assert CommandResponse.fromstring("<msg><status>3</status></msg>") \
    == CommandResponse("Arming", None)
  assert CommandResponse.fromstring("<msg><status>4</status></msg>") \
    == CommandResponse("Running", None)
  assert CommandResponse.fromstring("<msg><status>5</status></msg>") \
    == CommandResponse("Paused", None)
  assert CommandResponse.fromstring("<msg><status>6</status></msg>") \
    == CommandResponse("Ended", None)
  with pytest.raises(RuntimeError):
    CommandResponse.fromstring("<msg><status>10</status></msg>")
    CommandResponse.fromstring("<msg><status>-1</status></msg>")
    CommandResponse.fromstring("<msg><status1>0</status1></msg>")
    err = "<msg><status>0</status><error>ERROR</error></msg>"
    CommandResponse.fromstring(err)

def setup_mock_server():
  """
  Setup an TCP echo server.
  """
  # Setup a mocked tests
  HOST, PORT = "localhost", 0
  server = MockServer((HOST, PORT), MockRequestHandler)
  ip, port = server.server_address
  server_thread = threading.Thread(target=server.serve_forever)
  server_thread.daemon = True
  server_thread.start()
  return (ip, port)

def test_echo_sim():
  """
  An echo test with a TCP server: do we receive the right
  TELNET commands on the server side?

  """
  ip, port = setup_mock_server()
  # Simulations
  dev = STR4500(ip, port)
  tr_obj = lambda data: CommandResponse("Invalid scenario", data)
  assert dev.status() == tr_obj("NULL")
  for k, v in parse_sims_dictionary().iteritems():
    assert dev.select_scenario(v) == tr_obj("SC,%s" % v)
  assert dev.run_scenario() == tr_obj("RU")
  assert dev.scenario_duration() == "SC_DURATION"
  assert dev.end_scenario(stop_mode=0) == tr_obj("-,EN,0,0")
  assert dev.end_scenario(stop_mode=1) == tr_obj("-,EN,1,0")
  assert dev.rewind_scenario() == tr_obj("RW")
  # Tests across all channels.
  assert dev.set_power(on=True) == tr_obj("-,POW_ON,v1_a1,1,0,1,1")
  assert dev.set_power(on=False) == tr_obj("-,POW_ON,v1_a1,0,0,1,1")
  assert dev.set_power_mode(mode=0) == tr_obj("-,POW_MODE,v1_a1,0,0,1,1")
  assert dev.set_power_mode(mode=1) == tr_obj("-,POW_MODE,v1_a1,1,0,1,1")
  for power in xrange(0, 10):
    assert dev.set_power_level(level=float(power), absolute=True) \
      == tr_obj("-,POW_LEV,v1_a1,%s,0,1,1,1" % float(power))
    assert dev.set_power_level(level=float(power), absolute=False) \
      == tr_obj("-,POW_LEV,v1_a1,%s,0,1,1,0" % float(power))
  assert dev.set_prn(on=True) == tr_obj("-,PRN_CODE,0,1,1")
  assert dev.set_prn(on=False) == tr_obj("-,PRN_CODE,0,1,0")
  assert dev.enable_hardware(mode=True) == tr_obj("HARDWARE_ON,1")
  assert dev.enable_hardware(mode=False) == tr_obj("HARDWARE_ON,0")
  assert dev.enable_hardware(mode=True) == tr_obj("HARDWARE_ON,1")
  assert dev.enable_popups(mode=True) == tr_obj("POPUPS_ON,1")
  assert dev.enable_popups(mode=False) == tr_obj("POPUPS_ON,0")
  # Iterate through all the channels.
  for chan in xrange(0, 11):
    assert dev.chan.set_power(chan, on=True) == tr_obj("-,POW_ON,v1_a1,1,%s,1,0" % chan)
    assert dev.chan.set_power(chan, on=False) == tr_obj("-,POW_ON,v1_a1,0,%s,1,0" % chan)
    assert dev.chan.set_power_mode(chan, mode=0) == tr_obj("-,POW_MODE,v1_a1,0,%s,1,0" % chan)
    assert dev.chan.set_power_mode(chan, mode=1) == tr_obj("-,POW_MODE,v1_a1,1,%s,1,0" % chan)
    assert dev.chan.set_prn(chan, on=True)  == tr_obj("-,PRN_CODE,%s,0,1" % chan)
    assert dev.chan.set_prn(chan, on=False) == tr_obj("-,PRN_CODE,%s,0,0" % chan)
    # Iterate through all the power levels for all of the channels.
    for power in xrange(0, 10):
      assert dev.chan.set_power_level(chan, level=float(power), absolute=True) \
        == tr_obj("-,POW_LEV,v1_a1,%s,%s,1,0,1" % (float(power), chan))
      assert dev.chan.set_power_level(chan, level=float(power), absolute=False) \
        == tr_obj("-,POW_LEV,v1_a1,%s,%s,1,0,0" % (float(power), chan))

# Internal IP for live STR4500.
STR4500_IP = "192.168.1.169"

def test_simscount():
  """
  Check simulations.
  """
  assert len(parse_sims_dictionary()) == 69

def test_sims_integration():
  """
  Integration test simulation scenario validity.
  """

# TODO (Buro): Uncomment these once pytest handling for test selectors
# is properly figured out.
# def test_integration():
#   """
#   Runs test with a live STR4500.
#   """
#   with STR4500(STR4500_IP) as dev:
#     assert dev.set_power(on=True) == CommandResponse("Initialised", None)
#     assert dev.set_power(on=False) == CommandResponse("Initialised", None)
#     assert dev.set_power_mode(mode=0) == CommandResponse("Initialised", None)
#     assert dev.set_power_mode(mode=1) == CommandResponse("Initialised", None)
#     for power in xrange(0, 10):
#       assert dev.set_power_level(level=float(power), absolute=True) \
#         == CommandResponse("Initialised", None)
#       assert dev.set_power_level(level=float(power), absolute=False) \
#         == CommandResponse("Initialised", None)
#     assert dev.set_prn(on=True) == CommandResponse("Initialised", None)
#     assert dev.set_prn(on=False) == CommandResponse("Initialised", None)
#     assert dev.enable_hardware(mode=True) == CommandResponse("Initialised", None)
#     assert dev.enable_hardware(mode=False) == CommandResponse("Initialised", None)
#     assert dev.enable_hardware(mode=True) == CommandResponse("Initialised", None)
#     assert dev.enable_popups(mode=True) == CommandResponse("Initialised", None)
#     assert dev.enable_popups(mode=False) == CommandResponse("Initialised", None)
#     assert dev.scenario_duration() == "22"
#     assert dev.time() == 22

# def test_channel_integration():
#   """
#   Runs a test on channels with a live STR4500.
#   """
#   with STR4500(STR4500_IP) as dev:
#     # Iterate through all the channels.
#     for chan in xrange(0, 11):
#       assert dev.set_power(chan, on=True) \
#         == CommandResponse("Initialised", None)
#       assert dev.set_power(chan, on=False) \
#         == CommandResponse("Initialised", None)
#       assert dev.set_power_mode(chan, mode=0) \
#         == CommandResponse("Initialised", None)
#       assert dev.set_power_mode(chan, mode=1) \
#         == CommandResponse("Initialised", None)
#       assert dev.set_prn(chan, on=True) == CommandResponse("Initialised", None)
#       assert dev.set_prn(chan, on=False) == CommandResponse("Initialised", None)
#       assert dev.set_prn(chan, on=True) == CommandResponse("Initialised", None)
#       # Iterate through all the power levels for all of the channels.
#       for power in xrange(0, 10):
#         assert dev.set_power_level(chan, level=float(power), absolute=True) \
#           == CommandResponse("Initialised", None)
#         assert dev.set_power_level(chan, level=float(power), absolute=False) \
#           == CommandResponse("Initialised", None)

# def test_sat_integration():
#   """
#   Runs a test on satellites with a live STR4500.
#   """
#   with STR4500(STR4500_IP) as dev:
#     # Iterate through all the satellites.
#     for sat in xrange(1, 33):
#       assert dev.set_power(sat, on=True) \
#         == CommandResponse("Initialised", None)
#       assert dev.set_power(sat, on=False) \
#         == CommandResponse("Initialised", None)
#       assert dev.set_power_mode(sat, mode=0) \
#         == CommandResponse("Initialised", None)
#       assert dev.set_power_mode(sat, mode=1) \
#         == CommandResponse("Initialised", None)
#       # Iterate through all the power levels for all of the satellites.
#       for power in xrange(0, 11):
#         assert dev.set_power_level(sat, level=float(power), absolute=True) \
#           == CommandResponse("Initialised", None)
#         assert dev.set_power_level(sat, level=float(power), absolute=False) \
#           == CommandResponse("Initialised", None)
