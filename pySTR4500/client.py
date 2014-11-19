#!/usr/bin/env python
# Copyright (C) 2014 Swift Navigation Inc.
# API documentation:
# Copyright © Spirent Communications SW Ltd
# Contact: Bhaskar Mookerji <mookerji@swiftnav.com>
#
# This source is subject to the license found in the file 'LICENSE' which must
# be be distributed together with this source. All other rights reserved.
#
# THIS CODE AND INFORMATION IS PROVIDED "AS IS" WITHOUT WARRANTY OF ANY KIND,
# EITHER EXPRESSED OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND/OR FITNESS FOR A PARTICULAR PURPOSE.

"""
STR4500 driver using BSD Sockets.

The STR4500 is a multichannel RF signal generator for GPS signals. The
STR4500 driver here implements the Telnet interface to its SimPLEX
software (see pg. 1-13, "Chapter 6: Remote commands", of the "STR4500
GPS/SBAS Simulator with SimPLEX" user guide). Each command function
serializes a string tuple in the SimPLEX command dictionary and writes
it to a fixed socket connection.

This is currently a direct translation of the Telnet command
dictionary on a minimal, command-by-command basis with few other
external dependencies. It may be refactored in the future for safer
access to certain virtual resources (scenarios, GPS satellites, etc.).

"""

import socket
import xml.etree.ElementTree as ET

BUFFER_SIZE = 4096
SIMPLEX_PORT = 15650
STATUS_VALUES = {
  0x00 : "No scenario specified",
  0x01 : "Invalid scenario",
  0x02 : "Initialised",
  0x03 : "Arming",
  0x04 : "Running",
  0x05 : "Paused",
  0x06 : "Ended"
}
# test_string = "<msg><status>6</status></msg>"

class CommandResponse(object):
  """
  TCP API controller for the STR4500 GPS/SBAS Simulator with SimPLEX.

  Parameters
  ----------
  response : str
    XML string response from the STR4500.

  Returns
  ----------
  response : CommandResponse

  """

  def __init__(self, response):
    p = ET.fromstring(response)
    if p.find('status') is not None:
      try:
        self.status = STATUS_VALUES[int(p.find('status').text)]
      except KeyError:
        raise RuntimeError("Invalid STR4500 status.")
    else:
      raise RuntimeError("Invalid STR4500 response: status required.")
    if p.find('error') is not None:
      msg = p.find('error').text
      raise RuntimeError("STR4500 returned error: %s" % msg)
    self.data = float(p.find('data').text) if p.find('data') else None

  def __repr__(self):
    val = (self.status, self.data)
    formatted = "<CommandResponse (status = %s, data = %s)>"
    return formatted % val


class STR4500(object):
  """
  TCP API controller for the STR4500 GPS/SBAS Simulator with SimPLEX.

  Parameters
  ----------
  host : str
    IPv4 address or hostname. If you're running this off of a VM,
    probably the IPv4 address of your Windows VM. Defaults to
    localhost.
  port : int
    STR4500 Simplex socket is actually hardwired to port 15650 :( .

  Returns
  ----------
  controller : STR4500

  """

  def __init__(self, host="127.0.0.1", port=15650):
    self.host = host
    self.port = port
    self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
    self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    self._socket.connect((self.host, self.port))
    self._socket.setblocking(1)
    self.connected = self.null() is not None

  def __del__(self):
    if self._socket:
      self._socket.close()
      self._socket = None

  def __repr__(self):
    val = (self.host, self.port, self.connected)
    formatted = "<STR4500 (host = %s, port = %s, connected = %s)>"
    return formatted % val

  @staticmethod
  def encode(cmd):
    """
    Formats a command (as comma-delimited), for sending over the wire.

    STR4500 Telnet commands actually look like:
      "-,POW_LEV ,v1_a1,10.5,23,0,0,1"
      "RU"
      "0 00:05:00,EN,2"

    """
    return ','.join(map(str, cmd))

  def timestamp(self):
    """
    Timestamp is either: the time into run to apply command; or, if '-'
    command is applied, when command is received.

    """
    return "-"

  def _dispatch(self, msg):
    """
    Blocking I/O to the socket.

    Parameters
    ----------
    msg : str
      Command string

    Returns
    ----------
    response : str
      XML response string.

    """
    self._socket.send(msg)
    return self._socket.recv(BUFFER_SIZE)

  def _handle(self, cmd):
    """
    Given a command tuple, encode, issue, and decode.
    """
    return CommandResponse(self._dispatch(self.encode(cmd)))

  def select_scenario(self, filename):
    """
    Select scenario. select_scenario may be called before a scenario has run,
    or after a scenario has been rewound.

    Parameters
    ----------
    filename : str
      Windows filepath (example: "C:\\scenarios\\my.sim")

    Returns
    -------
    response : CommandResponse

    """
    cmd = ["SC", filename]
    return self._handle(cmd)

  def set_trigger(self, mode):
    """
    Set trigger mode to mode.:

    Parameters
    ----------
    mode : int
      Trigger mode:
      0 = Software trigger,
      1 = Ext trigger immediate,
      2 = Ext trigger on next 1pps edge.

    Returns
    -------
    response : CommandResponse

    """
    if mode not in [0, 1, 2]:
      raise ValueError("Invalid trigger mode.")
    cmd = ["TR", mode]
    return self._handle(cmd)

  def run_scenario(self):
    """
    Run selected scenario.

    Requires external pulse to start in trigger modes 1, 2.

    Returns
    -------
    response : CommandResponse

    """
    cmd = ["RU"]
    return self._handle(cmd)

  def null(self):
    """
    This command just elicits a response from SimPLEX.

    Returns
    -------
    response : CommandResponse

    """
    cmd = ["NULL"]
    return self._handle(cmd)

  def end_scenario(self, timestamp="-", stop_mode=0, save=True):
    """
    End running scenario.

    Parameters
    ----------
    timestamp : str, optional
      timestamp is either: the time into run to apply command; or, if
      "-" command is applied, when command is received. Defaults to
      "-".
    stop_mode : int, optional
      0 = stop (scenario left in ENDED state),
      1 = stop scenario and rewind to INITIALISED state,
      2 = stop scenario, rewind to INITIALISED state, rewind remote.
      command file and repeat command sequence in file (only applies
      to remote commands from file).
    save : int, optional
      True = save logged data at end of run
      False = don't save logged data

    Returns
    -------
    response : CommandResponse

    """
    if stop_mode not in [0, 1, 2]:
      raise ValueError("Invalid value of n.")
    cmd = [timestamp, "EN", stop_mode, 1 if save else 0]
    return self._handle(cmd)

  def rewind_scenario(self):
    """
    Rewind scenario.

    Called after scenario has been stopped by an end_scenario (with
    optional parameter [n not specified or 0].  Rewinds the scenario
    ready to run again or you can select another scenario to run.

    Returns
    -------
    response : CommandResponse
    """
    cmd = ["RW"]
    return self._handle(cmd)

#TODO (Buro): check boolean conversions.

  def power_on(self, on, all_chans, chan=None, sat=None, timestamp="-"):
    """
    Power ON / OFF.

    Parameters
    ----------
    on : bool
      True: = power ON; False = OFF
    all_chans : bool
      True = apply to all channels
      False = apply to specified channel or satellite only
    chan : int
      Channel number (0 to 11). You can specify either an channel or
      satellite, but not both.
    sat : int
      Satellite ID number (1 to 32).
    timestamp : str, optional
      timestamp is either: the time into run to apply command; or, if
      "-" command is applied, when command is received. Defaults to
      "-".

    Returns
    -------
    response : CommandResponse

    """
    vehicle_antenna = "v1_a1"
    if chan and sat:
      raise ValueError("Can't set both satellite and channel simultaneously.")
    elif chan and (0 <= chan < 12):
      cmd = [timestamp, "POW_ON", vehicle_antenna, 1 if on else 0, chan, 1,
             1 if all_chans else 0]
      return self._handle(cmd)
    elif sat and (1 <= sat < 33):
      cmd = [timestamp, "POW_ON", vehicle_antenna, 1 if on else 0, sat, 0,
             1 if all_chans else 0]
      return self._handle(cmd)
    else:
      raise ValueError("Invalid channel/satellite value.")

  def set_power_mode(self, all_chans, mode, timestamp="-", chan=None, sat=None):
    """
    Set power mode.

    Parameters
    ----------
    all_chans : bool
      True = apply to specified channel or satellite only
      False = apply to all channels
    mode : int
      0 = Absolute power
      1 = Relative to current simulation power
    chan : int
      Channel number (0 to 11). You can specify either an channel or
      satellite, but not both.
    sat : int
      Satellite ID number (1 to 32).
    timestamp : str, optional
      timestamp is either: the time into run to apply command; or, if
      "-" command is applied, when command is received. Defaults to
      "-".

    Returns
    -------
    response : CommandResponse

    """
    vehicle_antenna = "v1_a1"
    if chan and sat:
      raise ValueError("Can't set both satellite and channel simultaneously.")
    elif chan and (0 <= chan < 12):
      cmd = [timestamp, "POW_MODE", vehicle_antenna, mode, chan, 1,
             1 if all_chans else 0]
      return self._handle(cmd)
    elif sat and (1 <= sat < 33):
      cmd = [timestamp, "POW_MODE", vehicle_antenna, mode, sat, 1,
             1 if all_chans else 0]
      return self._handle(cmd)
    else:
      raise ValueError("Invalid channel/satellite value.")

  def set_power_level(self, all_chans, level, absolute, chan=None, sat=None,
                      timestamp="-"):
    """
    Set power level.

    Parameters
    ----------
    all_chans : bool
      True = apply to specified channel or satellite only, False =
      apply to all channels
    level : float
      Power level, dB (with respect to the Stanag minimum).
    absolute : bool
      True = relative to current simulated power,
      False = absolute power level
    chan : int
      Channel number (0 to 11). You can specify either an channel or
      satellite, but not both.
    sat : int
      Satellite ID number (1 to 32).
    timestamp : str, optional
      timestamp is either: the time into run to apply command; or, if
      "-" command is applied, when command is received. Defaults to
      "-".

    Returns
    -------
    response : CommandResponse

    """
    vehicle_antenna = "v1_a1"
    if chan and sat:
      raise ValueError("Can't set both satellite and channel simultaneously.")
    elif chan and (0 <= chan < 12):
      cmd = [timestamp, "POW_LEV", vehicle_antenna, level, chan, 1,
             1 if all_chans else 0, 1 if absolute else 0]
      return self._handle(cmd)
    elif sat and (1 <= sat < 33):
      cmd = [timestamp, "POW_LEV", vehicle_antenna, level, chan, 0,
             1 if all_chans else 0, 1 if absolute else 0]
      return self._handle(cmd)
    else:
      raise ValueError("Invalid channel/satellite value.")

  def set_prn_code(self, on, all_chans, chan, timestamp="-"):
    """
    Set PRN code on/off.

    Parameters
    ----------
    on : boolean
      True = PRN code OFF,
      False = PRN code ON
    all_chans : boolean
      True = apply to specified channel or satellite only,
      False = apply to all channels
    chan : int
      channel no. (0 to 11)
    timestamp : str, optional
      timestamp is either: the time into run to apply command; or, if
      "-" command is applied, when command is received.

    Returns
    -------
    response : CommandResponse

    """
    if 0 <= chan < 12:
      cmd = [timestamp, "PRN_CODE", chan, all_chans, on]
      return self._handle(cmd)
    else:
      raise ValueError("Invalid value of chan.")

  def set_no_hardware_flag(self, mode):
    """
    Set/Reset No Hardware flag.

    Parameters
    ----------
    mode : bool
      True = set No hardware mode, see (5.4.3.1); False = hardware
      enabled.

    Returns
    -------
    response : CommandResponse

    """
    cmd = ["HARDWARE_ON", 1 if mode else 0]
    return self._handle(cmd)

  def set_popups(self, mode):
    """
    Set/Disable Popup Messages on Fatal Error.

    Errors are still recorded in the message_log.txt file and this
    does not alter the settings of the Msg Reports dialog

    Parameters
    ----------
    mode : bool
      True = suppress Popup messages,
      False = enable popup messages.

    Returns
    -------
    response : CommandResponse

    """
    cmd = ["POPUPS_ON", 1 if mode else 0]
    return self._handle(cmd)

  def time(self):
    """
    Get time into run, Returns time into run in integer seconds.

    Returns
    -------
    response : CommandResponse

    """
    cmd = ["TIME"]
    return self._handle(cmd).data

  def scenario_duration(self):
    """
    Get duration of scenario. Returns duration in the form d hh:mm.

    Returns
    -------
    response : CommandResponse

    """
    cmd = ["SC_DURATION"]
    return self._handle(cmd).data

# if __name__ == "__main__":
#     client = STR4500()
#     client.null()
