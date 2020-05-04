import numpy as np            # pylint: disable=unused-import
import typing                 # pylint: disable=unused-import
from nomad.metainfo import (  # pylint: disable=unused-import
    MSection, MCategory, Category, Package, Quantity, Section, SubSection, SectionProxy,
    Reference
)
from nomad.metainfo.legacy import LegacyDefinition

from nomad.datamodel.metainfo import public
from nomad.datamodel.metainfo import common

m_package = Package(
    name='fplo_nomadmetainfo_json',
    description='None',
    a_legacy=LegacyDefinition(name='fplo.nomadmetainfo.json'))


class section_run(public.section_run):

    m_def = Section(validate=False, extends_base_section=True, a_legacy=LegacyDefinition(name='section_run'))

    x_fplo_program_version_sub = Quantity(
        type=str,
        shape=[],
        description='''
        FPLO sub version
        ''',
        a_legacy=LegacyDefinition(name='x_fplo_program_version_sub'))

    x_fplo_program_compilation_options = Quantity(
        type=str,
        shape=[],
        description='''
        FPLO compilation options
        ''',
        a_legacy=LegacyDefinition(name='x_fplo_program_compilation_options'))


class section_system(public.section_system):

    m_def = Section(validate=False, extends_base_section=True, a_legacy=LegacyDefinition(name='section_system'))

    x_fplo_reciprocal_cell = Quantity(
        type=np.dtype(np.float64),
        shape=[3, 3],
        unit='1 / meter',
        description='''
        Reciprocal Lattice vectors (in Cartesian coordinates). The first index runs over
        the $x,y,z$ Cartesian coordinates, and the second index runs over the 3 lattice
        vectors.
        ''',
        categories=[public.configuration_core],
        a_legacy=LegacyDefinition(name='x_fplo_reciprocal_cell'))

    x_fplo_atom_idx = Quantity(
        type=np.dtype(np.int32),
        shape=['number_of_atoms'],
        description='''
        FPLO-internal index for each atom
        ''',
        a_legacy=LegacyDefinition(name='x_fplo_atom_idx'))

    x_fplo_atom_wyckoff_idx = Quantity(
        type=np.dtype(np.int32),
        shape=['number_of_atoms'],
        description='''
        Wyckoff position index of each atom
        ''',
        a_legacy=LegacyDefinition(name='x_fplo_atom_wyckoff_idx'))

    x_fplo_atom_cpa_block = Quantity(
        type=np.dtype(np.int32),
        shape=['number_of_atoms'],
        description='''
        CPA block of each atom
        ''',
        a_legacy=LegacyDefinition(name='x_fplo_atom_cpa_block'))

    x_fplo_structure_type = Quantity(
        type=str,
        shape=[],
        description='''
        FPLO structure type: Crystal/Molecule
        ''',
        a_legacy=LegacyDefinition(name='x_fplo_structure_type'))


class section_method(public.section_method):

    m_def = Section(validate=False, extends_base_section=True, a_legacy=LegacyDefinition(name='section_method'))

    x_fplo_xc_functional_number = Quantity(
        type=np.dtype(np.int32),
        shape=[],
        description='''
        FPLO number xc functional
        ''',
        a_legacy=LegacyDefinition(name='x_fplo_xc_functional_number'))

    x_fplo_xc_functional = Quantity(
        type=str,
        shape=[],
        description='''
        FPLO notation of xc functional
        ''',
        a_legacy=LegacyDefinition(name='x_fplo_xc_functional'))

    x_fplo_dft_plus_u_projection_type = Quantity(
        type=str,
        shape=[],
        description='''
        FPLO notation of DFT+U projection
        ''',
        a_legacy=LegacyDefinition(name='x_fplo_dft_plus_u_projection_type'))

    x_fplo_dft_plus_u_functional = Quantity(
        type=str,
        shape=[],
        description='''
        FPLO notation of DFT+U functional
        ''',
        a_legacy=LegacyDefinition(name='x_fplo_dft_plus_u_functional'))


class section_dft_plus_u_orbital(common.section_dft_plus_u_orbital):

    m_def = Section(validate=False, extends_base_section=True, a_legacy=LegacyDefinition(name='section_dft_plus_u_orbital'))

    x_fplo_dft_plus_u_orbital_element = Quantity(
        type=str,
        shape=[],
        description='''
        FPLO: Atom/Orbital dependent DFT+U property: element
        ''',
        a_legacy=LegacyDefinition(name='x_fplo_dft_plus_u_orbital_element'))

    x_fplo_dft_plus_u_orbital_species = Quantity(
        type=np.dtype(np.int32),
        shape=[],
        description='''
        FPLO: Atom/Orbital dependent DFT+U property: species index
        ''',
        a_legacy=LegacyDefinition(name='x_fplo_dft_plus_u_orbital_species'))

    x_fplo_dft_plus_u_orbital_F0 = Quantity(
        type=np.dtype(np.float64),
        shape=[],
        description='''
        FPLO: Atom/Orbital dependent DFT+U property: value F0
        ''',
        categories=[public.energy_value],
        a_legacy=LegacyDefinition(name='x_fplo_dft_plus_u_orbital_F0'))

    x_fplo_dft_plus_u_orbital_F2 = Quantity(
        type=np.dtype(np.float64),
        shape=[],
        description='''
        FPLO: Atom/Orbital dependent DFT+U property: value F2
        ''',
        categories=[public.energy_value],
        a_legacy=LegacyDefinition(name='x_fplo_dft_plus_u_orbital_F2'))

    x_fplo_dft_plus_u_orbital_F4 = Quantity(
        type=np.dtype(np.float64),
        shape=[],
        description='''
        FPLO: Atom/Orbital dependent DFT+U property: value F4
        ''',
        categories=[public.energy_value],
        a_legacy=LegacyDefinition(name='x_fplo_dft_plus_u_orbital_F4'))

    x_fplo_dft_plus_u_orbital_F6 = Quantity(
        type=np.dtype(np.float64),
        shape=[],
        description='''
        FPLO: Atom/Orbital dependent DFT+U property: value F6
        ''',
        categories=[public.energy_value],
        a_legacy=LegacyDefinition(name='x_fplo_dft_plus_u_orbital_F6'))


m_package.__init_metainfo__()
