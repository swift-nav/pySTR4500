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
Utilities for loading simulation scenarios.
"""

SIMS_DICTIONARY = "./sim_scenarios.txt"

def parse_sims_dictionary(path = SIMS_DICTIONARY):
  """
  Get an index of simPLEX simulations on the Windows guest, for easy
  use with the client.

  Parameters
  ----------
  filepath : str, optional
    filepath to index of scenarios. Defaults to SIMS_DICTIONARY.

  Returns
  ----------
  response : dict
    Mapping of index to Windows guest filepath.

  """
  index = {}
  with open(path) as f:
    for line in f:
       (key, val) = line.split(",")
       index[int(key)] = val.rstrip() # rstrip not working?
  return index
