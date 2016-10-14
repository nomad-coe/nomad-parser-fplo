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


# lookup table translating relativistic treatment from fplo to NOMAD
FPLO_RELATIVISTIC = {
    'non': '',
    'scalar': 'scalar_relativistic',
    'KH scalar': 'scalar_relativistic',
    'full': '4_component_relativistic',
}


class ParserFplo14(object):
    """main place to keep the parser status, open ancillary files,..."""
    def __init__(self):
        self.parserInfo = FploC.PARSER_INFO_DEFAULT.copy()
        self.cachingLevelForMetaName = {}
        for name in FploC.META_INFO.infoKinds:
            # set all temporaries to caching-only
            if name.startswith('x_fplo_t_'):
                self.cachingLevelForMetaName[name] = CachingLevel.Cache
        self.coverageIgnoreList = [
            # ignore empty lines
            r"\s*",
            # table separators
            r"^\s*[=%-]+\s*$",
            r"^\s*\|\s*\|\s*$",
        ]
        self.coverageIgnore = None
        unit_conversion.register_userdefined_quantity('usrTpibbohr', '1/bohr', 2*math.pi)

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
                   ] + self.SMs_crystal_structure() + [
                   ] + self.SMs_method() + [
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
                      startReStr=r"\s*Start: content of =.in\s*$",
                      adHoc=self.adHoc_input_content
                   ),
               ] + self.SMs_sym_msg() + [
               ],
            ),
        ]
        return result

    def adHoc_cs_structure_type(self, parser):
        if parser.lastMatch['x_fplo_structure_type'] == 'Crystal':
            parser.backend.addArrayValues('configuration_periodic_dimensions',
                                          np.array([True, True, True]))
        elif parser.lastMatch['x_fplo_structure_type'] == 'Molecule':
            parser.backend.addArrayValues('configuration_periodic_dimensions',
                                          np.array([False, False, False]))
        else:
            raise RuntimeError('unexpected value for x_fplo_structure_type: ',
                               parser.lastMatch['x_fplo_structure_type'])

    def SMs_crystal_structure(self):
        result = [
            SM(name='csHead',
               startReStr=r"\s*CALCULATION OF CRYSTALL STRUCTURE\s*$",
               subMatchers=[
                   SM(name='csInputHead',
                      startReStr=r"\s*INPUT DATA\s*$",
                   ),
                   SM(name='csSymmHead',
                      startReStr=r"\s*SYMMETRY CREATION\s*$",
                      subMatchers=[
                          SM(name='csLatticeVectors',
                             startReStr=r"\s*lattice vectors\s*$",
                             subMatchers=[
                                 SM(name='csLatA1',
                                    startReStr=r"\s*a1\s*:\s+" + FploC.re_vec('x_fplo_t_vec_a', 'bohr') + r"\s*$",
                                 ),
                                 SM(name='csLatA2',
                                    startReStr=r"\s*a2\s*:\s+" + FploC.re_vec('x_fplo_t_vec_a', 'bohr') + r"\s*$",
                                 ),
                                 SM(name='csLatA3',
                                    startReStr=r"\s*a3\s*:\s+" + FploC.re_vec('x_fplo_t_vec_a', 'bohr') + r"\s*$",
                                 ),
                             ],
                          ),
                          SM(name='csReciprocalVectors',
                             startReStr=r"\s*reciprocial lattice vectors / 2\*Pi\s*$",
                             subMatchers=[
                                 SM(name='csLatB1',
                                    startReStr=r"\s*g1\s*:\s+" + FploC.re_vec('x_fplo_t_vec_b', 'usrTpibbohr') + r"\s*$",
                                 ),
                                 SM(name='csLatB2',
                                    startReStr=r"\s*g2\s*:\s+" + FploC.re_vec('x_fplo_t_vec_b', 'usrTpibbohr') + r"\s*$",
                                 ),
                                 SM(name='csLatB3',
                                    startReStr=r"\s*g3\s*:\s+" + FploC.re_vec('x_fplo_t_vec_b', 'usrTpibbohr') + r"\s*$",
                                 ),
                             ],
                          ),
                      ],
                   ),
                   SM(name='csAtomsHead',
                      startReStr=r"\s*UNIT CELL CREATION\s*$",
                      subMatchers=[
                          SM(name='csAtomsPositionHead',
                             startReStr=r"\s*No.  Element WPS CPA-Block\s+X\s+Y\s+Z\s*$",
                             subMatchers=[
                                 SM(name='csAtomPositions', repeats=True,
                                    startReStr=(
                                        r"\s*(?P<x_fplo_t_atom_idx>" + RE_i + r")" +
                                        r"\s+(?P<x_fplo_t_atom_labels>\S+)" +
                                        r"\s+(?P<x_fplo_t_atom_wyckoff_idx>" + RE_i + r")" +
                                        r"\s+(?P<x_fplo_t_atom_cpa_block>" + RE_i + r")" +
                                        r"\s+" + FploC.re_vec('x_fplo_t_atom_positions', 'bohr') +
                                        r"\s*$"
                                    ),
                                 ),
                             ],
                          ),
                      ],
                   ),
                   SM(name='csStructureType',
                      startReStr=r"Structure type:\s*(?P<x_fplo_structure_type>\S+)\s*$",
                      adHoc=self.adHoc_cs_structure_type
                   ),
               ],
            ),
        ]
        return result

    def SMs_method(self):
        result = [
            SM(name='mRelativistic',
               startReStr=r"\s*(?P<x_fplo_t_relativity_method>.*?)\s*relativistic\s*calculation!\s*$",
               adHoc=lambda p: p.backend.addValue(
                   'relativity_method', FPLO_RELATIVISTIC[p.lastMatch['x_fplo_t_relativity_method']])
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

    def onClose_section_system(
            self, backend, gIndex, section):
        # store direct lattice matrix and inverse for transformation crystal <-> cartesian
        if section['x_fplo_t_vec_a_x'] is not None:
            self.amat = np.array([
                section['x_fplo_t_vec_a_x'][-3:], section['x_fplo_t_vec_a_y'][-3:], section['x_fplo_t_vec_a_z'][-3:],
            ], dtype=np.float64).T
            # store inverse for transformation cartesian -> crystal
            try:
                self.amat_inv = np.linalg.inv(self.amat)
            except np.linalg.linalg.LinAlgError:
                raise Exception("error inverting bravais matrix " + str(self.amat))
            LOGGER.info('NewCell')
        else:
            raise Exception("missing bravais vectors")
        backend.addArrayValues('simulation_cell', self.amat)
        # store reciprocal lattice matrix and inverse for transformation crystal <-> cartesian
        if section['x_fplo_t_vec_b_x'] is not None:
            self.bmat = np.array([
                section['x_fplo_t_vec_b_x'], section['x_fplo_t_vec_b_y'], section['x_fplo_t_vec_b_z'],
            ], dtype=np.float64).T
            # store inverse for transformation cartesian -> crystal
            try:
                self.bmat_inv = np.linalg.inv(self.bmat)
            except np.linalg.linalg.LinAlgError:
                raise Exception("error inverting reciprocal cell matrix")
        elif section['x_fplo_t_vec_a_x'] is not None:
            # we got new lattice vectors, but no reciprocal ones, calculate
            # on-the-fly
            LOGGER.error('calculating bmat on the fly from amat')
            abmat = np.zeros((3,3), dtype=np.float64)
            abmat[0] = np.cross(self.amat[1],self.amat[2])
            abmat[1] = np.cross(self.amat[2],self.amat[0])
            abmat[2] = np.cross(self.amat[0],self.amat[1])
            abmat *= 2*math.pi / np.dot(abmat[0],self.amat[0])
            self.bmat = abmat
            # store inverse for transformation cartesian -> crystal
            try:
                self.bmat_inv = np.linalg.inv(self.bmat)
            except np.linalg.linalg.LinAlgError:
                raise Exception("error inverting reciprocal cell matrix")
        else:
            raise Exception("missing reciprocal cell vectors")
        backend.addArrayValues('x_fplo_reciprocal_cell', self.bmat)
        # stuff we parsed from atom position table
        if section['x_fplo_t_atom_labels'] is not None:
            backend.addArrayValues('atom_labels', np.asarray(
                section['x_fplo_t_atom_labels']))
        if section['x_fplo_t_atom_idx'] is not None:
            backend.addArrayValues('x_fplo_atom_idx', np.asarray(
                section['x_fplo_t_atom_idx']))
        if section['x_fplo_t_atom_wyckoff_idx'] is not None:
            backend.addArrayValues('x_fplo_atom_wyckoff_idx', np.asarray(
                section['x_fplo_t_atom_wyckoff_idx']))
        if section['x_fplo_t_atom_cpa_block'] is not None:
            backend.addArrayValues('x_fplo_atom_cpa_block', np.asarray(
                section['x_fplo_t_atom_cpa_block']))
        if section['x_fplo_t_atom_positions_x'] is not None:
            backend.addArrayValues('atom_positions', np.asarray([
                section['x_fplo_t_atom_positions_x'],
                section['x_fplo_t_atom_positions_y'],
                section['x_fplo_t_atom_positions_z'],
            ], dtype=np.float64).T)

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
