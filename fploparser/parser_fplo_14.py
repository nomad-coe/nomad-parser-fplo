#!/usr/bin/env python
# Copyright 2016-2017 Henning Glawe
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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
from . import FploCommon as FploC
import calendar
from nomadcore.parser_backend import valueForStrValue
from .FploCommon import RE_f, RE_i, cRE_f, cRE_i
from nomadcore.parser_backend import valueForStrValue
from . import FploInputParser


LOGGER = logging.getLogger(__name__)


# lookup table translating relativistic treatment from fplo to NOMAD
FPLO_RELATIVISTIC = {
    'non': '',
    'scalar': 'scalar_relativistic',
    'KH scalar': 'scalar_relativistic',
    'full': '4_component_relativistic',
}

# lookup table translating XC functional from fplo to NOMAD
FPLO_XC_FUNCTIONAL = {
    'Exchange only                (LSDA)': [
        { 'XC_functional_name': 'LDA_X' },
    ],
    'von Barth Hedin              (LSDA)': [
        { 'XC_functional_name': 'LDA_X' },
        { 'XC_functional_name': 'LDA_C_VBH' },
    ],
    'Perdew and Zunger            (LSDA)': [
        { 'XC_functional_name': 'LDA_X' },
        { 'XC_functional_name': 'LDA_C_PZ' },
    ],
    'Perdew Wang 92               (LSDA)': [
        { 'XC_functional_name': 'LDA_X' },
        { 'XC_functional_name': 'LDA_C_PW' },
    ],
    'Perdew Burke Ernzerhof 96    (GGA)':  [
        { 'XC_functional_name': 'GGA_X_PBE' },
        { 'XC_functional_name': 'GGA_C_PBE' },
    ],
}

FPLO_DFT_PLUS_U_PROJECTION_TYPE = {
    'orthogonal': 'orthogonalized atomic',
}

FPLO_DFT_PLUS_U_FUNCTIONAL = {
    'LSDA+U Atomic limit      (AL)': 'fully localized limit',
    'LSDA+U Around mean field (AMF/OP)': 'around mean field',
}

class ParserFplo14(object):
    """main place to keep the parser status, open ancillary files,..."""
    def __init__(self, metaInfoEnv):
        self.parserInfo = FploC.PARSER_INFO_DEFAULT.copy()
        self.cachingLevelForMetaName = {}
        for name in metaInfoEnv.infoKinds:
            # set all temporaries to caching-only
            if name.startswith('x_fplo_t_'):
                self.cachingLevelForMetaName[name] = CachingLevel.Cache
        self.coverageIgnoreList = [
            # ignore empty lines
            r"\s*",
            # table separators
            r"^\s*[=%-]+\s*$",
            r"^\s*\|\s*\|\s*$",
            # table separators in LSDA+U
            r"^\s*LSDA\+U:\s*[=%-]+\s*$",
        ]
        self.coverageIgnore = None
        unit_conversion.register_userdefined_quantity('usrTpibbohr', '1/bohr', 2*math.pi)

    def parse(self):
        self.coverageIgnore = re.compile(r"^(?:" + r"|".join(self.coverageIgnoreList) + r")$")
        mainFunction(self.mainFileDescription(), metaInfoEnv, self.parserInfo,
                     cachingLevelForMetaName=self.cachingLevelForMetaName,
                     superContext=self)

    def mainFileDescription(self):
        # assemble matchers and submatchers
        result = SM(name='root',
            startReStr=r"$",
            subMatchers=[
                SM(name='newrun', repeats=True, forwardMatch=True,
                   startReStr=r"\s*\|\s*FULL-POTENTIAL LOCAL-ORBITAL MINIMUM BASIS BANDSTRUCTURE CODE\s*\|\s*$",
                   sections=['section_run'],
                   fixedStartValues={
                       'program_name': 'fplo',
                       'program_basis_set_type': 'local-orbital minimum-basis',
                   },
                   subMatchers=[
                       SM(name='method_structure',
                          # parent has forwardMatch set, allows to
                          # replicate for opening method/system sections, both closed by SCF matcher
                          startReStr=r"\s*\|\s*FULL-POTENTIAL LOCAL-ORBITAL MINIMUM BASIS BANDSTRUCTURE CODE\s*\|\s*$",
                          sections=['section_method', 'section_system'],
                          subMatchers=[
                          ] + self.SMs_header() + [
                          ] + self.SMs_input() + [
                          ] + self.SMs_crystal_structure() + [
                          ] + self.SMs_method() + [
                          ],
                       ),
                       SM(name='start_scf',
                          startReStr=r"\s*SCF: Iteration version\s*\(\s*\d+\) : Iterat\s*:\s*(?:.*?)\s*$",
                          sections=['section_single_configuration_calculation'],
                          subMatchers=self.SMs_scf(),
                       ),
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
        input_parser = FploInputParser.FploInputParser(
            None,
            annotated_line_callback=self.callback_annotated_input_line)
        while True:
            fInLine = parser.fIn.readline()
            if re.match(r'^\s*-{60,}\s*$', fInLine):
                self.callback_annotated_input_line(fInLine)
                break
            input_parser.parse_line(fInLine)
        input_parser.onEnd_of_file()

    def callback_annotated_input_line(self, annotated_input_line):
        minfo = {
            # raw line
            'fInLine': '', # fInLine,
            'fInLineNr': self.parser.fIn.lineNr,
            # information about SimpleMatcher
            'matcherName': 'tokenizer',
            'defFile': 'FploInputParser.py',
            'defLine': 0,
            'matcher_does_nothing': False,
            'which_re': 'tokenizer',
            # classification of match
            'matchFlags': 1,
            'match': 3, # 0 - no, 1 - partial, 3 - full
            'coverageIgnore': 0, # 0 - no, 1 - local, 3 - global
            # overall span of match, and spans of group captures
            'span': [],
            # capture group names
            'matcherGroup': [],
            # we have pre-highlighted line
            'highlighted': annotated_input_line,
        }
        self.parser.annotator.annotate(minfo)

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
                      subMatchers=[
                          SM(name='startEchoInputDelimiter',
                             startReStr=r'^\s*-{60,}\s*$',
                             adHoc=self.adHoc_input_content,
                          ),
                      ],
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
            SM(name='mXC',
               startReStr=r"\s*XC version :\s*(?P<x_fplo_xc_functional_number>\d+)\s*-\s*(?P<x_fplo_xc_functional>.*?)\s*$",
               adHoc=lambda p: self.addSectionDictList(
                   p.backend, 'section_XC_functionals',
                   FPLO_XC_FUNCTIONAL[p.lastMatch['x_fplo_xc_functional']])
            ),
            SM(name='mLSDApU_stuff',
               startReStr=r"\s*LSDA\+U:\s*-+\s*$",
               subMatchers=[
                   SM(name='mLSDApU_projection',
                      startReStr=r"\s*LSDA\+U:\s*Projection\s*:\s*(?P<x_fplo_dft_plus_u_projection_type>\S+?)\s*$",
                      adHoc=lambda p: p.backend.addValue('dft_plus_u_projection_type',
                          FPLO_DFT_PLUS_U_PROJECTION_TYPE[p.lastMatch['x_fplo_dft_plus_u_projection_type']]),
                   ),
                   SM(name='mLSDApU_functional',
                      startReStr=r"\s*LSDA\+U:\s*Functional\s*:\s*(?P<x_fplo_dft_plus_u_functional>.+?)\s*$",
                      adHoc=lambda p: p.backend.addValue('dft_plus_u_functional',
                          FPLO_DFT_PLUS_U_FUNCTIONAL[p.lastMatch['x_fplo_dft_plus_u_functional']]),
                   ),
                   SM(name='mLSDApU_n_correlated_states',
                      startReStr=r"\s*LSDA\+U:\s*\d+\s*Correlated states",
                      subMatchers=[
                          SM(name='mLSDApU_correlated_states_header',
                             startReStr=r'\s*LSDA\+U:\s*sort\s+el\.\s+state\s+F0\s+F2\s+F4\s+F6\s+U\s+J\s*$',
                             subMatchers=[
                                 SM(name='mLSDApU_correlated_states_in_EV',
                                    startReStr=r'\s*LSDA\+U:\s*\(in eV\)\s*$',
                                 ),
                                 SM(name='mLSDApU_correlated_states_line', repeats=True,
                                    startReStr=(
                                        r"\s*LSDA\+U:" +
                                        r"\s*(?P<x_fplo_t_dft_plus_u_species_subshell_species>\d+)" +
                                        r"\s+(?P<x_fplo_t_dft_plus_u_species_subshell_element>\S+)" +
                                        r"\s+(?P<x_fplo_t_dft_plus_u_species_subshell_subshell>\S+)" +
                                        r"\s+(?P<x_fplo_t_dft_plus_u_species_subshell_F0__eV>" + RE_f + r")" +
                                        r"\s+(?P<x_fplo_t_dft_plus_u_species_subshell_F2__eV>" + RE_f + r")" +
                                        r"\s+(?P<x_fplo_t_dft_plus_u_species_subshell_F4__eV>" + RE_f + r")" +
                                        r"\s+(?P<x_fplo_t_dft_plus_u_species_subshell_F6__eV>" + RE_f + r")" +
                                        r"\s+(?P<x_fplo_t_dft_plus_u_species_subshell_U__eV>" + RE_f + r")" +
                                        r"\s+(?P<x_fplo_t_dft_plus_u_species_subshell_J__eV>" + RE_f + r")" +
                                        r"\s*$"
                                    )
                                 ),
                             ],
                          ),
                          SM(name='mLSDApU_correlated_sites_header',
                             startReStr=r'\s*LSDA\+U:\s+site\s+el\.\s+udef\s+state\s+ubi1\s+ubi2\s*$',
                             subMatchers=[
                                 SM(name='mLSDApU_correlated_sites_line', repeats=True,
                                    startReStr=(
                                        r"\s*LSDA\+U:" +
                                        r"\s*(?P<x_fplo_t_dft_plus_u_site_index>\d+)" +
                                        r"\s+(?P<x_fplo_t_dft_plus_u_site_element>\S+)" +
                                        r"\s*(?P<x_fplo_t_dft_plus_u_site_species>\d+)" +
                                        r"\s+(?P<x_fplo_t_dft_plus_u_site_subshell>\S+)" +
                                        r"\s+(?P<x_fplo_t_dft_plus_u_site_ubi1>\d+)" +
                                        r"\s+(?P<x_fplo_t_dft_plus_u_site_ubi2>\d+)" +
                                        r"\s*$"
                                    )
                                 ),
                             ],
                          ),
                      ],
                   ),
               ],
            ),
        ]
        return result

    def SMs_scf(self):
        result = [
            SM(name='new_iter', repeats=True,
               startReStr=r"\s*SCF: iteration\s*(?:\d+)\s*dimension\s*(?:\d+)\s*last deviation\s*u=\s*(?:" + RE_f + r")\s*$",
               sections=['section_scf_iteration'],
               subMatchers=[
                   SM(name='estimate_eFermi',
                      startReStr=r"\s*Estimating Fermi energy\s*\.\.\.\s*$",
                      subMatchers=[
                          SM(name='tetwts_eFermi',
                             startReStr=(
                                r"\s*TETWTS: Fermi energy:\s*(?P<x_fplo_t_energy_reference_fermi_iteration__hartree>" + RE_f + r")\s*;" +
                                r"\s*(?:" + RE_f + r")\s*electrons" +
                                r"\s*$"
                             ),
                          ),
                      ],
                   ),
                   SM(name='header_eTot',
                      startReStr=r"\s*==========\s*TOTAL ENERGY\s*==========\s*$",
                      subMatchers=[
                          SM(name='header2_eTot',
                             startReStr=r"\s*total energy\s+kinetic energy\s+potential energy\s+ex\.-corr\. energy\s*$",
                             subMatchers=[
                                 SM(name='eTot',
                                    startReStr=(
                                        r"EE:" +
                                        r"\s*(?P<energy_total_scf_iteration__eV>" + RE_f + r")" +
                                        r"\s+(?P<electronic_kinetic_energy_scf_iteration__eV>" + RE_f + r")" +
                                        r"\s+(?:" + RE_f + r")" +
                                        r"\s+(?:" + RE_f + r")" +
                                        r"\s*$"
                                    )
                                 ),
                             ],
                          ),
                          SM(name='header2_eTot_DFTU',
                             startReStr=r"\s*total energy\s+kinetic energy\s+potential energy\s+ex\.-corr\. energy\s*"
                                        r"LS(?:AD|DA)\+U energy\s*$",
                             subMatchers=[
                                 SM(name='eTot',
                                    startReStr=(
                                        r"EE:" +
                                        r"\s*(?P<energy_total_scf_iteration__eV>" + RE_f + r")" +
                                        r"\s+(?P<electronic_kinetic_energy_scf_iteration__eV>" + RE_f + r")" +
                                        r"\s+(?:" + RE_f + r")" +
                                        r"\s+(?:" + RE_f + r")" +
                                        r"\s+(?:" + RE_f + r")" +
                                        r"\s*$"
                                    )
                                 ),
                             ],
                          ),
                      ]
                   ),
               ],
            ),
        ]
        return result

    def onOpen_section_scf_iteration(
            self, backend, gIndex, section):
        self.section['scf_iteration'] = section
        self.sectionIdx['scf_iteration'] = gIndex

    def onClose_section_scf_iteration(
            self, backend, gIndex, section):
        eFermi = np.array([
            section['x_fplo_t_energy_reference_fermi_iteration'][-1],
            section['x_fplo_t_energy_reference_fermi_iteration'][-1],
        ])
        backend.addArrayValues('energy_reference_fermi_iteration', eFermi)

    def get_dft_plus_u_per_species_orbital(self, section_method):
        dft_plus_u_per_species_orbital = {}
        for species_orbital_idx in range(len(section_method['x_fplo_t_dft_plus_u_species_subshell_species'])):
            species = section_method['x_fplo_t_dft_plus_u_species_subshell_species'][species_orbital_idx]
            subshell = section_method['x_fplo_t_dft_plus_u_species_subshell_subshell'][species_orbital_idx]
            if dft_plus_u_per_species_orbital.get(species,None) is None:
                dft_plus_u_per_species_orbital[species] = {}
            dft_plus_u_per_species_orbital[species][subshell] = {
                # code-independent orbital data
                'dft_plus_u_orbital_label': subshell,
                'dft_plus_u_orbital_U':
                    section_method['x_fplo_t_dft_plus_u_species_subshell_U'][species_orbital_idx],
                'dft_plus_u_orbital_J':
                    section_method['x_fplo_t_dft_plus_u_species_subshell_J'][species_orbital_idx],
                # code-specific orbital data
                'x_fplo_dft_plus_u_orbital_species': species,
                'x_fplo_dft_plus_u_orbital_element':
                    section_method['x_fplo_t_dft_plus_u_species_subshell_element'][species_orbital_idx],
                'x_fplo_dft_plus_u_orbital_F0':
                    section_method['x_fplo_t_dft_plus_u_species_subshell_F0'][species_orbital_idx],
                'x_fplo_dft_plus_u_orbital_F2':
                    section_method['x_fplo_t_dft_plus_u_species_subshell_F2'][species_orbital_idx],
                'x_fplo_dft_plus_u_orbital_F4':
                    section_method['x_fplo_t_dft_plus_u_species_subshell_F4'][species_orbital_idx],
                'x_fplo_dft_plus_u_orbital_F6':
                    section_method['x_fplo_t_dft_plus_u_species_subshell_F6'][species_orbital_idx],
            }
        return dft_plus_u_per_species_orbital

    def get_dft_plus_u_orbitals(self, section_method):
        dft_plus_u_orbitals = []
        dft_plus_u_per_species_orbital = self.get_dft_plus_u_per_species_orbital(section_method)
        for dft_plus_u_idx in range(len(section_method['x_fplo_t_dft_plus_u_site_index'])):
            site = section_method['x_fplo_t_dft_plus_u_site_index'][dft_plus_u_idx]
            element = section_method['x_fplo_t_dft_plus_u_site_element'][dft_plus_u_idx]
            species = section_method['x_fplo_t_dft_plus_u_site_species'][dft_plus_u_idx]
            orbital = section_method['x_fplo_t_dft_plus_u_site_subshell'][dft_plus_u_idx]
            dft_plus_u_orbital = dft_plus_u_per_species_orbital[species][orbital].copy()
            dft_plus_u_orbital['dft_plus_u_orbital_atom'] = site - 1 # FPLO site counts one-based
            dft_plus_u_orbitals.append(dft_plus_u_orbital)
        return dft_plus_u_orbitals

    def onOpen_section_method(
            self, backend, gIndex, section):
        self.sectionIdx['method'] = gIndex
        self.section['method'] = section

    def onClose_section_method(
            self, backend, gIndex, section):
        # check for DFT+U vs. DFT
        if section['x_fplo_dft_plus_u_projection_type'] is None:
            backend.addValue('electronic_structure_method', 'DFT')
        else:
            backend.addValue('electronic_structure_method', 'DFT+U')
            self.addSectionDictList(backend, 'section_dft_plus_u_orbital',
                                    self.get_dft_plus_u_orbitals(section))

    def onOpen_section_run(
            self, backend, gIndex, section):
        self.section['run'] = section
        self.sectionIdx['run'] = gIndex

    def onClose_section_run(
            self, backend, gIndex, section):
        # assemble version number
        backend.addValue('program_version',
                         section['x_fplo_t_program_version_main'][-1] + '-' +
                         section['x_fplo_t_program_version_release'][-1])
        # map list of hosts to dict
        backend.addValue('run_hosts',
                         {h:1 for h in section['x_fplo_t_run_hosts']})

    def onOpen_section_system(
            self, backend, gIndex, section):
        self.section['system'] = section
        self.sectionIdx['system'] = gIndex

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

    def onOpen_section_single_configuration_calculation(
            self, backend, gIndex, section):
        self.section['single_configuration_calculation'] = section
        self.sectionIdx['single_configuration_calculation'] = gIndex

    def onClose_section_single_configuration_calculation(
            self, backend, gIndex, section):
        backend.addValue('single_configuration_calculation_to_system_ref', self.sectionIdx['system'])
        backend.addValue('single_configuration_to_calculation_method_ref', self.sectionIdx['method'])
        scf_iter = self.section['scf_iteration']
        backend.addValue(
            'energy_total',
            scf_iter['energy_total_scf_iteration'][-1]
        )
        backend.addArrayValues(
            'energy_reference_fermi',
            np.array(scf_iter['energy_reference_fermi_iteration'][-1])
        )

    def initialize_values(self):
        """allows to reset values if the same superContext is used to parse
        different files"""
        self.section = {}
        self.sectionIdx = {}

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

    def addSectionDictList(self, backend, section_name, section_dict_list):
        for section_dict in section_dict_list:
            self.addSectionDict(backend, section_name, section_dict)

    def addSectionDict(self, backend, section_name, section_dict):
        gIndex = backend.openSection(section_name)
        for key, value in sorted(section_dict.items()):
            if isinstance(value, (list,dict)):
                backend.addValue(key, value)
            else:
                backend.addValue(key, value)
        backend.closeSection(section_name, gIndex)


class FploParser():
    """ A proper class envolop for running this parser from within python. """
    def __init__(self, backend, **kwargs):
        self.backend_factory = backend

    def parse(self, mainfile):
        from unittest.mock import patch
        logging.info('fplo parser started')
        logging.getLogger('nomadcore').setLevel(logging.WARNING)
        backend = self.backend_factory("fplo.nomadmetainfo.json")
        parserInfo = {'name': 'fplo-parser', 'version': '1.0'}
        context = ParserFplo14(backend.metaInfoEnv())

        with patch.object(sys, 'argv', ['<exe>', '--uri', 'nmd://uri', mainfile]):
            mainFunction(
                context.mainFileDescription(),
                None,
                parserInfo=FploC.PARSER_INFO_DEFAULT.copy(),
                cachingLevelForMetaName=context.cachingLevelForMetaName,
                superContext=context,
                superBackend=backend)

        return backend