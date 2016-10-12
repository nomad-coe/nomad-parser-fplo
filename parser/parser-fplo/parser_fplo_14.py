#!/usr/bin/env python
import setup_paths
from nomadcore.simple_parser import mainFunction, SimpleMatcher as SM, CachingLevel
from nomadcore.local_meta_info import loadJsonFile, InfoKindEl
import os
import sys
import json
import re
import logging
import nomadcore.unit_conversion.unit_conversion as unit_conversion
import math
import numpy as np
import FploCommon as FploC
import calendar
from nomadcore.parser_backend import valueForStrValue
from FploCommon import RE_f, RE_i, cRE_f, cRE_i
from nomadcore.parser_backend import valueForStrValue


LOGGER = logging.getLogger(__name__)


class ParserFplo14(object):
    """main place to keep the parser status, open ancillary files,..."""
    def __init__(self):
        self.parserInfo = FploC.PARSER_INFO_DEFAULT.copy()
        self.cachingLevelForMetaName = {}
        for name in FploC.META_INFO.infoKinds:
            # set all temporaries to caching-only
            if name.startswith('x_fplo_t_'):
                self.cachingLevelForMetaName[name] = CachingLevel.Cache
        # common prosa in espresso output
        self.coverageIgnoreList = [
            # ignore empty lines
            r"\s*",
            # table separators
            r"^\s*[=%-]+\s*$",
            r"^\s*\|\s*\|\s*$",
        ]
        self.coverageIgnore = None

    def parse(self):
        self.coverageIgnore = re.compile(r"^(?:" + r"|".join(self.coverageIgnoreList) + r")$")
        mainFunction(self.mainFileDescription(), FploC.META_INFO, self.parserInfo,
                     cachingLevelForMetaName=self.cachingLevelForMetaName,
                     superContext=self)

    def mainFileDescription(self):
        # assemble matchers and submatchers
        result = SM(name='root',
            startReStr=r"$",
            subMatchers=[
                SM(name='newrun', repeats=True,
                   startReStr=r"\s*\|\s*FULL-POTENTIAL LOCAL-ORBITAL MINIMUM BASIS BANDSTRUCTURE CODE\s*\|\s*$",
                   sections=['section_run', 'section_method', 'section_system'],
                   fixedStartValues={
                       'program_name': 'fplo',
                       'program_basis_set_type': 'local-orbital minimum-basis',
                   },
                   subMatchers=[
                   ] + self.SMs_header() + [
                   ] + self.SMs_input() + [
                   ]
                ),
            ]
        )
        return result

    def SMs_header(self):
        result = [
            SM(name='copyrightspam', repeats=True, coverageIgnore=True,
               startReStr=r"\s*\|\s*(?:" + r"|".join([
                   r"FULL RELATIVISTIC VERSION",
                   r"by K\. Koepernik, A\.Ernst and H\.Eschrig \(2003\)",
                   r"relativistic version by Ingo Opahle",
                   r"LSDA\+U by Igor Chaplygin",
                   r"Any publication of results obtained by this program",
                   r"has to include the citation:",
                   r"K\.Koepernik and H\.Eschrig, Phys\. Rev\. B 59, 1743 \(1999\)",
                   r"Any publication of CPA results obtained by this program",
                   r"additionally has to include the citation:",
                   r"K\. Koepernik, B\. Velicky, R\. Hayn and H\. Eschrig,",
                   r"Phys\. Rev\. B 55, 5717 \(1997\)",
               ]) + r")\s*\|\s*$",
            ),
            SM(name='versMain',
               startReStr=r"\s*\|\s*main\s+version\s*:\s*(?P<x_fplo_t_program_version_main>\S+)\s*\|\s*$",
               subMatchers=[
                   SM(name='versSub',
                      startReStr=r"\s*\|\s*sub\s+version\s*:\s*(?P<x_fplo_program_version_sub>\S+)\s*\|\s*$",
                   ),
                   SM(name='versRelease',
                      startReStr=r"\s*\|\s*release\s*:\s*(?P<x_fplo_t_program_version_release>\S+)\s*\|\s*$",
                   ),
                   SM(name='compileOpts', repeats=True,
                      startReStr=r"\s*\|\s*compiled with\s*(?P<x_fplo_program_compilation_options>.*?)\s*\|\s*$",
                   ),
                   SM(name='runDate',
                      startReStr=r"\s*\|\s*date\s*:\s*(?P<time_run_date_start__strFploDate>.+?)\s*\|\s*$",
                   ),
                   SM(name='runHost',
                      startReStr=r"\s*\|\s*host\s*:\s*(?P<x_fplo_t_run_hosts>.+?)\s*\|\s*$"
                   ),
               ],
            ),
        ]
        return result

    def SMs_sym_msg(self):
        # msg appears twice, so new generator
        result = [
            SM(name='inpSymInfo',
               startReStr=r"\s*INFORMATION in MODULE SYMMETRY\(crystal_structure_setup\):\s*$",
               subMatchers=[
                   SM(name='InfoHexAxis1',
                      startReStr=r"\s*INFORMATION: (?P<message_info_run>\(makeunitcell\): Third hexagonal axis angle != 120 degree!)\s*$",
                   ),
                   SM(name='InfoHexAxis2',
                      startReStr=r"\s*(?P<message_info_run>I will correct it !)\s*$",
                   ),
               ],
            ),
        ]
        return result

    def adHoc_input_content(self, parser):
        LOGGER.error("TODO: parse C-like echoed input")

    def SMs_input(self):
        result = [
            SM(name='inpSym',
               startReStr=r"\s*File =\.sym exists!\s*$",
               subMatchers=[
               ] + self.SMs_sym_msg() + [
               ],
            ),
            SM(name='inpIn',
               startReStr=r"\s*File =\.in exists!\s*$",
               subMatchers=[
                   SM(name='inpInCompound',
                      startReStr=r"\s*Compound\s*:\s*(?P<system_name>.*?)\s*$",
                   ),
                   SM(name='startEchoInput',
                      startReStr=r"\s*Start: content of =.in\s*",
                      adHoc=self.adHoc_input_content
                   ),
               ] + self.SMs_sym_msg() + [
               ],
            ),
        ]
        return result

    def onClose_section_run(
            self, backend, gIndex, section):
        # assemble version number
        backend.addValue('program_version',
                         section['x_fplo_t_program_version_main'][-1] + '-' +
                         section['x_fplo_t_program_version_release'][-1])
        # map list of hosts to dict
        backend.addValue('run_hosts',
                         {h:1 for h in section['x_fplo_t_run_hosts']})

    def initialize_values(self):
        """allows to reset values if the same superContext is used to parse
        different files"""
        self.sectionIdx = {}
        self.openSectionIdx = {}
        self.tmp = {}
        self.alat = None
        self.section = {}

    def startedParsing(self, path, parser):
        """called when parsing starts"""
        self.parser = parser
        # reset values if same superContext is used to parse different files
        self.initialize_values()

    def strValueTransform_strFploDate(self, fplo_date):
        if fplo_date is None:
            return None
        epoch = 0
        match = re.match(
            r"(?P<dow>[A-Za-z]+)\s+(?P<month>[A-Za-z]+)\s+(?P<day>\d+)\s+" +
            r"(?P<hour>\d+):\s*(?P<minute>\d+):\s*(?P<second>\d+)\s+" +
            r"(?P<year>\d+)\s*",
            fplo_date)
        if match:
            month = FploC.MONTH_NUMBER[match.group('month')]
            epoch = calendar.timegm(
                (int(match.group('year')), int(month), int(match.group('day')),
                 int(match.group('hour')), int(match.group('minute')), int(match.group('second'))))
        else:
            raise RuntimeError("unparsable date: %s", fplo_date)
        return(epoch)
    strValueTransform_strFploDate.units = 's'

if __name__ == "__main__":
    parser = ParserFplo14()
    parser.parse()
