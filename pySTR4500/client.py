#!/usr/bin/env python
#
# Copyright (C) 2014 Swift Navigation Inc.
# API documentation:
# Copyright (C) Spirent Communications SW Ltd.
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
VEHICLE_ANTENNA = "v1_a1"

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

  def __init__(self, status=None, data=None):
    self.status = status
    self.data = data

  def __eq__(self, other):
    return self.__dict__ == other.__dict__

  def __repr__(self):
    val = (self.status, self.data)
    formatted = "<CommandResponse (status = %s, data = %s)>"
    return formatted % val

  @staticmethod
  def fromstring(response):
    """
    Construct a CommandResponse from an XML string.

    Parameters
    ----------
    response : str
      XML string response from the STR4500.

    Returns
    ----------
    response : CommandResponse

    """
    # TODO (Buro): Change this to throw an exception. We should never
    # have an empty response.
    if not response:
      return CommandResponse()
    p = ET.fromstring(response)
    status = None
    if p.find('status') is not None:
      try:
        status = STATUS_VALUES[int(p.find('status').text)]
      except KeyError:
        raise RuntimeError("Invalid STR4500 status.")
    else:
      raise RuntimeError("Invalid STR4500 response: status required.")
    if p.find('error') is not None:
      msg = p.find('error').text
      raise RuntimeError("STR4500 returned error: %s" % msg)
    data = p.find('data').text if p.find('data') is not None else None
    return CommandResponse(status, data)

def encode(cmd):
  """
  Formats a command (vector->comma-delimited string), for sending
  over the wire.

  STR4500 Telnet commands actually look like:
    "-,POW_LEV ,v1_a1,10.5,23,0,0,1"
    "RU"
    "0 00:05:00,EN,2"

  """
  return ','.join(map(str, cmd))

def dispatch(host, port, msg):
  """
  Blocking I/O to the socket.

  Parameters
  ----------
  host : str
    IPv4 address or hostname. If you're running this off of a VM,
    probably the IPv4 address of your Windows VM. Defaults to
    localhost.
  port : int
    STR4500 Simplex socket is actually hardwired to port 15650 :( .
  msg : str
    Command string

  Returns
  ----------
  response : str
    XML response string.

  """
  sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
  sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
  try:
    sock.connect((host, port))
    sock.setblocking(1)
    sock.sendall(msg)
    return sock.recv(BUFFER_SIZE)
  finally:
    sock.close()

def handle(host, port, cmd):
  """
  Given a command tuple, encode, issue, and decode.

  Parameters
  ----------
  host : str
    IPv4 address or hostname. If you're running this off of a VM,
    probably the IPv4 address of your Windows VM. Defaults to
    localhost.
  port : int
    STR4500 Simplex socket is actually hardwired to port 15650 :( .
  cmd : [str]
    Vector of command parameters.

  Returns
  ----------
  response : CommandResponse

  """
  return CommandResponse.fromstring(dispatch(host, port, encode(cmd)))

class Channel(object):
  """
  Controller for PRN channel.
  """

  is_chan = int(True)
  all_chans = int(False)

  def __init__(self, host, port):
    self.host = host
    self.port = port

  @staticmethod
  def is_valid(chan):
    return bool(chan is not None and 0 <= chan <= 11)

  def set_power(self, chan, on, timestamp="-"):
    """
    Power ON/OFF channel.

    Parameters
    ----------
    chan : int
      Channel number (0 to 11).
    on : bool
      True = power ON;
      False = OFF
    timestamp : str, optional
      timestamp is either: the time into run to apply command; or, if
      "-" command is applied, when command is received. Defaults to
      "-".

    Returns
    -------
    response : CommandResponse

    """
    if not Channel.is_valid(chan):
      raise ValueError("Invalid channel value.")
    cmd = [timestamp, "POW_ON", VEHICLE_ANTENNA, int(on), chan,
           Channel.is_chan, Channel.all_chans]
    return handle(self.host, self.port, cmd)

  def set_power_mode(self, chan, mode, timestamp="-"):
    """
    Set channel power mode.

    Parameters
    ----------
    chan : int
      Channel number (0 to 11).
    mode : int
      0 = Absolute power
      1 = Relative to current simulation power
    timestamp : str, optional
      timestamp is either: the time into run to apply command; or, if
      "-" command is applied, when command is received. Defaults to
      "-".

    Returns
    -------
    response : CommandResponse

    """
    if not Channel.is_valid(chan):
      raise ValueError("Invalid channel value.")
    cmd = [timestamp, "POW_MODE", VEHICLE_ANTENNA, mode, chan,
           Channel.is_chan, Channel.all_chans]
    return handle(self.host, self.port, cmd)

  def set_power_level(self, chan, level, absolute, timestamp="-"):
    """
    Set channel power level.

    Parameters
    ----------
    chan : int
      Channel number (0 to 11).
    level : float
      Power level, dB (with respect to the Stanag minimum).
    absolute : bool
      True = absolute power level,
      False = relative to current simulated power.
    timestamp : str, optional
      timestamp is either: the time into run to apply command; or, if
      "-" command is applied, when command is received. Defaults to
      "-".

    Returns
    -------
    response : CommandResponse

    """
    if not Channel.is_valid(chan):
      raise ValueError("Invalid channel value.")
    cmd = [timestamp, "POW_LEV", VEHICLE_ANTENNA, level, chan, Channel.is_chan,
           Channel.all_chans, int(absolute)]
    return handle(self.host, self.port, cmd)

  def set_prn(self, chan, on, timestamp="-"):
    """
    Set channel PRN code on/off.

    Parameters
    ----------
    chan : int
      channel no. (0 to 11)
    on : bool
      True = PRN code ON,
      False = PRN code OFF.
    timestamp : str, optional
      timestamp is either: the time into run to apply command; or, if
      "-" command is applied, when command is received.

    Returns
    -------
    response : CommandResponse

    """
    if not Channel.is_valid(chan):
      raise ValueError("Invalid channel value.")
    cmd = [timestamp, "PRN_CODE", chan, Channel.all_chans, int(on)]
    return handle(self.host, self.port, cmd)

class Satellite(object):
  """
  Controller by satellite ID.
  """

  is_chan = int(True)
  all_chans = int(False)

  def __init__(self, host, port):
    self.host = host
    self.port = port

  @staticmethod
  def is_valid(sat):
    return bool(sat is not None and 0 < sat <= 32)

  def set_power(self, sat, on, timestamp="-"):
    """
    Power ON/OFF satellite.

    Parameters
    ----------
    sat : int
      Satellite number (1 to 32).
    on : bool
      True = power ON;
      False = OFF
    timestamp : str, optional
      timestamp is either: the time into run to apply command; or, if
      "-" command is applied, when command is received. Defaults to
      "-".

    Returns
    -------
    response : CommandResponse

    """
    cmd = [timestamp, "POW_ON", VEHICLE_ANTENNA, int(on), sat,
           Satellite.is_chan, Satellite.all_chans]
    return handle(self.host, self.port, cmd)

  def set_power_mode(self, sat, mode, timestamp="-"):
    """
    Set satellite power mode.

    Parameters
    ----------
    sat : int
      Satellite number (1 to 32).
    mode : int
      0 = Absolute power
      1 = Relative to current simulation power
    timestamp : str, optional
      timestamp is either: the time into run to apply command; or, if
      "-" command is applied, when command is received. Defaults to
      "-".

    Returns
    -------
    response : CommandResponse

    """
    if not Satellite.is_valid(sat):
      raise ValueError("Invalid satellite value.")
    cmd = [timestamp, "POW_MODE", VEHICLE_ANTENNA, mode, sat,
           Satellite.is_chan, Satellite.all_chans]
    return handle(self.host, self.port, cmd)

  def set_power_level(self, sat, level, absolute, timestamp="-"):
    """
    Set satellite power level.

    Parameters
    ----------
    sat : int
      Satellite ID number (1 to 32).
    level : float
      Power level, dB (with respect to the Stanag minimum).
    absolute : bool
      True = absolute power level
      False = relative to current simulated power.
    timestamp : str, optional
      timestamp is either: the time into run to apply command; or, if
      "-" command is applied, when command is received. Defaults to
      "-".

    Returns
    -------
    response : CommandResponse

    """
    if not Satellite.is_valid(sat):
      raise ValueError("Invalid satellite value.")
    cmd = [timestamp, "POW_LEV", VEHICLE_ANTENNA, level, sat, Satellite.is_chan,
           Satellite.all_chans, int(absolute)]
    return handle(self.host, self.port, cmd)

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

  chan = 0
  is_chan = int(True)
  all_chans = int(True)

  def __init__(self, host="127.0.0.1", port=15650):
    self.host = host
    self.port = port
    # Issue a status check for network connection.
    self.connected = self.status() is not None
    self.chan = Channel(self.host, self.port)
    self.sat = Satellite(self.host, self.port)

  def __repr__(self):
    val = (self.host, self.port, self.connected)
    formatted = "<STR4500 (host = %s, port = %s, connected = %s)>"
    return formatted % val

  def select_scenario(self, filename):
    """
    Select scenario. select_scenario may be called before a scenario has run,
    or after a scenario has been rewound. See pySTR4500 for easy selection
    of sims.

    Parameters
    ----------
    filename : str
      Windows filepath (example: "C:\\scenarios\\my.sim")

    Returns
    -------
    response : CommandResponse

    """
    cmd = ["SC", filename]
    return handle(self.host, self.port, cmd)

  def set_trigger(self, mode):
    """
    Set trigger mode to mode.

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
    return handle(self.host, self.port, cmd)

  def run_scenario(self):
    """
    Run selected scenario.

    Requires external pulse to start in trigger modes 1, 2.

    Returns
    -------
    response : CommandResponse

    """
    cmd = ["RU"]
    return handle(self.host, self.port, cmd)

  def status(self):
    """
    Elicit a status response from SimPLEX.

    Returns
    -------
    response : CommandResponse

    """
    cmd = ["NULL"]
    return handle(self.host, self.port, cmd)

  def end_scenario(self, stop_mode=0, save=False, timestamp="-"):
    """
    End running scenario.

    Parameters
    ----------
    stop_mode : int, optional
      0 = stop (scenario left in ENDED state),
      1 = stop scenario and rewind to INITIALISED state,
      2 = stop scenario, rewind to INITIALISED state, rewind remote.
      command file and repeat command sequence in file (only applies
      to remote commands from file).
    save : int, optional
      True = save logged data at end of run
      False = don't save logged data
    timestamp : str, optional
      timestamp is either: the time into run to apply command; or, if
      "-" command is applied, when command is received. Defaults to
      "-".

    Returns
    -------
    response : CommandResponse

    """
    if stop_mode not in [0, 1, 2]:
      raise ValueError("Invalid value of n.")
    cmd = [timestamp, "EN", stop_mode, int(save)]
    return handle(self.host, self.port, cmd)

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
    return handle(self.host, self.port, cmd)

  def set_power(self, on, timestamp="-"):
    """
    Power ON/OFF all channels.

    Parameters
    ----------
    on : bool
      True = power ON;
      False = OFF
    timestamp : str, optional
      timestamp is either: the time into run to apply command; or, if
      "-" command is applied, when command is received. Defaults to
      "-".

    Returns
    -------
    response : CommandResponse

    """
    cmd = [timestamp, "POW_ON", VEHICLE_ANTENNA, int(on), STR4500.chan,
           STR4500.is_chan, STR4500.all_chans]
    return handle(self.host, self.port, cmd)

  def set_power_mode(self, mode, timestamp="-"):
    """
    Set power mode for all channels.

    Parameters
    ----------
    mode : int
      0 = Absolute power
      1 = Relative to current simulation power
    timestamp : str, optional
      timestamp is either: the time into run to apply command; or, if
      "-" command is applied, when command is received. Defaults to
      "-".

    Returns
    -------
    response : CommandResponse

    """
    cmd = [timestamp, "POW_MODE", VEHICLE_ANTENNA, mode,
           STR4500.chan, STR4500.is_chan, STR4500.all_chans]
    return handle(self.host, self.port, cmd)

  def set_power_level(self, level, absolute, timestamp="-"):
    """
    Set power level on all channels.

    Parameters
    ----------
    level : float
      Power level, dB (with respect to the Stanag minimum).
    absolute : bool
      True = absolute power level,
      False = relative to current simulated power.
    timestamp : str, optional
      timestamp is either: the time into run to apply command; or, if
      "-" command is applied, when command is received. Defaults to
      "-".

    Returns
    -------
    response : CommandResponse

    """
    cmd = [timestamp, "POW_LEV", VEHICLE_ANTENNA, level, STR4500.chan,
           STR4500.is_chan, STR4500.all_chans, int(absolute)]
    return handle(self.host, self.port, cmd)

  def set_prn(self, on=True, timestamp="-"):
    """
    Set PRN code on/off on all channels.

    Parameters
    ----------
    on : bool
      True = PRN code ON,
      False = PRN code OFF.
    timestamp : str, optional
      timestamp is either: the time into run to apply command; or, if
      "-" command is applied, when command is received.

    Returns
    -------
    response : CommandResponse

    """
    cmd = [timestamp, "PRN_CODE", STR4500.chan, STR4500.all_chans, int(on)]
    return handle(self.host, self.port, cmd)

  def enable_hardware(self, mode=True):
    """
    Set/Reset No Hardware flag.

    Parameters
    ----------
    mode : bool
      True = Enable hardware,
      False = Set No hardware mode: see (5.4.3.1);.

    Returns
    -------
    response : CommandResponse

    """
    cmd = ["HARDWARE_ON", int(mode)]
    return handle(self.host, self.port, cmd)

  def enable_popups(self, mode=True):
    """
    Set/Disable Popup Messages on Fatal Error.

    Errors are still recorded in the message_log.txt file and this
    does not alter the settings of the Msg Reports dialog

    Parameters
    ----------
    mode : bool
      True = Enable popup messages,
      False = Suppress Popup messages.

    Returns
    -------
    response : CommandResponse

    """
    cmd = ["POPUPS_ON", int(mode)]
    return handle(self.host, self.port, cmd)

  def time(self):
    """
    Get time into run.

    Returns
    -------
    data : float
      Time into run in integer seconds.

    """
    cmd = ["TIME"]
    return int(handle(self.host, self.port, cmd).data)

  def scenario_duration(self):
    """
    Get duration of scenario.

    Returns
    -------
    data : str
      Returns duration in the form d hh:mm.

    """
    cmd = ["SC_DURATION"]
    return handle(self.host, self.port, cmd).data

#TODO (Buro): fix this.
# if __name__ == "__main__":
#     client = STR4500()
#     client.null()
