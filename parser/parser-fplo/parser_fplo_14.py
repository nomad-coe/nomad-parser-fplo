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
                   subMatchers=[
                   ] + self.sm_copyrightspam() + [
                   ]
                ),
            ]
        )
        return result

    def sm_copyrightspam(self):
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
            )
        ]
        return result

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

if __name__ == "__main__":
    parser = ParserFplo14()
    parser.parse()
