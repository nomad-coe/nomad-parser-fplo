import setup_paths
import calendar
import json
import os
import re
import numpy as np
import logging
from nomadcore.local_meta_info import loadJsonFile, InfoKindEl
from nomadcore.unit_conversion.unit_conversion import convert_unit
from nomadcore.simple_parser import mainFunction, SimpleMatcher as SM, CachingLevel

############################################################
# This file contains functions and constants that are needed
# by more than one parser.
############################################################


LOGGER = logging.getLogger(__name__)

# fortran float, alternate too-long-for-field fortran marker
RE_f = r"(?:[+-]?\d+(?:\.\d+)?(?:[eEdD][+-]?\d+)?|\*+)"
cRE_f = re.compile(RE_f)
# fortran int, alternate too-long-for-field fortran marker
RE_i = r"(?:[+-]?\d+|\*+)"
cRE_i = re.compile(RE_i)
NAN = float('nan')

def re_vec(name, units='', split="\s+"):
    """generator for 3-component vector regex"""
    if units:
        units = '__' + units
    res = (
        r'(?P<' + name + r'_x' + units + r'>' + RE_f + r')' + split +
        r'(?P<' + name + r'_y' + units + r'>' + RE_f + r')' + split +
        r'(?P<' + name + r'_z' + units + r'>' + RE_f + r')'
        )
    return res


# loading metadata from
# nomad-meta-info/meta_info/nomad_meta_info/fplo.nomadmetainfo.json
META_INFO = loadJsonFile(
    filePath=os.path.normpath(os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "../../../../nomad-meta-info/meta_info/nomad_meta_info/fplo.nomadmetainfo.json")),
    dependencyLoader=None,
    extraArgsHandling=InfoKindEl.ADD_EXTRA_ARGS,
    uri=None)[0]

PARSER_INFO_DEFAULT = {
  "name": "parser_fplo",
  "version": "0.0.1"
}

# constants for date conversion
MONTHS = [ 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
           'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec' ]
MONTH_NUMBER = { MONTHS[num]: num+1 for num in range(0,12) }
