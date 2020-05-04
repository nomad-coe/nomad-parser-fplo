import numpy as np            # pylint: disable=unused-import
import typing                 # pylint: disable=unused-import
from nomad.metainfo import (  # pylint: disable=unused-import
    MSection, MCategory, Category, Package, Quantity, Section, SubSection, SectionProxy,
    Reference
)
from nomad.metainfo.legacy import LegacyDefinition

from nomad.datamodel.metainfo import public

m_package = Package(
    name='fplo_temporaries_nomadmetainfo_json',
    description='None',
    a_legacy=LegacyDefinition(name='fplo.temporaries.nomadmetainfo.json'))


class section_run(public.section_run):

    m_def = Section(validate=False, extends_base_section=True, a_legacy=LegacyDefinition(name='section_run'))

    x_fplo_t_program_version_main = Quantity(
        type=str,
        shape=[],
        description='''
        temporary: FPLO main version
        ''',
        a_legacy=LegacyDefinition(name='x_fplo_t_program_version_main'))

    x_fplo_t_program_version_release = Quantity(
        type=str,
        shape=[],
        description='''
        temporary: FPLO release number
        ''',
        a_legacy=LegacyDefinition(name='x_fplo_t_program_version_release'))

    x_fplo_t_run_hosts = Quantity(
        type=str,
        shape=[],
        description='''
        temporary: FPLO run hosts
        ''',
        a_legacy=LegacyDefinition(name='x_fplo_t_run_hosts'))


class section_system(public.section_system):

    m_def = Section(validate=False, extends_base_section=True, a_legacy=LegacyDefinition(name='section_system'))

    x_fplo_t_vec_a_x = Quantity(
        type=np.dtype(np.float64),
        shape=[],
        description='''
        Temporary storage for direct lattice vectors, x-component
        ''',
        a_legacy=LegacyDefinition(name='x_fplo_t_vec_a_x'))

    x_fplo_t_vec_a_y = Quantity(
        type=np.dtype(np.float64),
        shape=[],
        description='''
        Temporary storage for direct lattice vectors, y-component
        ''',
        a_legacy=LegacyDefinition(name='x_fplo_t_vec_a_y'))

    x_fplo_t_vec_a_z = Quantity(
        type=np.dtype(np.float64),
        shape=[],
        description='''
        Temporary storage for direct lattice vectors, z-component
        ''',
        a_legacy=LegacyDefinition(name='x_fplo_t_vec_a_z'))

    x_fplo_t_vec_b_x = Quantity(
        type=np.dtype(np.float64),
        shape=[],
        description='''
        Temporary storage for reciprocal lattice vectors, x-component
        ''',
        a_legacy=LegacyDefinition(name='x_fplo_t_vec_b_x'))

    x_fplo_t_vec_b_y = Quantity(
        type=np.dtype(np.float64),
        shape=[],
        description='''
        Temporary storage for reciprocal lattice vectors, y-component
        ''',
        a_legacy=LegacyDefinition(name='x_fplo_t_vec_b_y'))

    x_fplo_t_vec_b_z = Quantity(
        type=np.dtype(np.float64),
        shape=[],
        description='''
        Temporary storage for reciprocal lattice vectors, z-component
        ''',
        a_legacy=LegacyDefinition(name='x_fplo_t_vec_b_z'))

    x_fplo_t_atom_positions_x = Quantity(
        type=np.dtype(np.float64),
        shape=[],
        description='''
        Temporary storage for atom positions, x-component
        ''',
        a_legacy=LegacyDefinition(name='x_fplo_t_atom_positions_x'))

    x_fplo_t_atom_positions_y = Quantity(
        type=np.dtype(np.float64),
        shape=[],
        description='''
        Temporary storage for atom positions, y-component
        ''',
        a_legacy=LegacyDefinition(name='x_fplo_t_atom_positions_y'))

    x_fplo_t_atom_positions_z = Quantity(
        type=np.dtype(np.float64),
        shape=[],
        description='''
        Temporary storage for atom positions, z-component
        ''',
        a_legacy=LegacyDefinition(name='x_fplo_t_atom_positions_z'))

    x_fplo_t_atom_idx = Quantity(
        type=np.dtype(np.int32),
        shape=[],
        description='''
        Temporary storage for FPLO atom index
        ''',
        a_legacy=LegacyDefinition(name='x_fplo_t_atom_idx'))

    x_fplo_t_atom_labels = Quantity(
        type=str,
        shape=[],
        description='''
        Temporary storage for FPLO atom labels
        ''',
        a_legacy=LegacyDefinition(name='x_fplo_t_atom_labels'))

    x_fplo_t_atom_wyckoff_idx = Quantity(
        type=np.dtype(np.int32),
        shape=[],
        description='''
        Temporary storage for FPLO Wyckoff position index of each atom
        ''',
        a_legacy=LegacyDefinition(name='x_fplo_t_atom_wyckoff_idx'))

    x_fplo_t_atom_cpa_block = Quantity(
        type=np.dtype(np.int32),
        shape=[],
        description='''
        Temporary storage for FPLO CPA block of each atom
        ''',
        a_legacy=LegacyDefinition(name='x_fplo_t_atom_cpa_block'))


class section_method(public.section_method):

    m_def = Section(validate=False, extends_base_section=True, a_legacy=LegacyDefinition(name='section_method'))

    x_fplo_t_relativity_method = Quantity(
        type=str,
        shape=[],
        description='''
        Temporary storage for FPLO relativistic method
        ''',
        a_legacy=LegacyDefinition(name='x_fplo_t_relativity_method'))

    x_fplo_t_dft_plus_u_species_subshell_species = Quantity(
        type=np.dtype(np.int32),
        shape=[],
        description='''
        Temporary storage for FPLO per species/(n,l)subshell DFT+U species
        ''',
        a_legacy=LegacyDefinition(name='x_fplo_t_dft_plus_u_species_subshell_species'))

    x_fplo_t_dft_plus_u_species_subshell_element = Quantity(
        type=str,
        shape=[],
        description='''
        Temporary storage for FPLO per species/(n,l)subshell DFT+U element
        ''',
        a_legacy=LegacyDefinition(name='x_fplo_t_dft_plus_u_species_subshell_element'))

    x_fplo_t_dft_plus_u_species_subshell_subshell = Quantity(
        type=str,
        shape=[],
        description='''
        Temporary storage for FPLO per species/(n,l)subshell DFT+U (n,l)subshell
        ''',
        a_legacy=LegacyDefinition(name='x_fplo_t_dft_plus_u_species_subshell_subshell'))

    x_fplo_t_dft_plus_u_species_subshell_F0 = Quantity(
        type=np.dtype(np.float64),
        shape=[],
        description='''
        Temporary storage for FPLO per species/(n,l)subshell DFT+U F0
        ''',
        a_legacy=LegacyDefinition(name='x_fplo_t_dft_plus_u_species_subshell_F0'))

    x_fplo_t_dft_plus_u_species_subshell_F2 = Quantity(
        type=np.dtype(np.float64),
        shape=[],
        description='''
        Temporary storage for FPLO per species/(n,l)subshell DFT+U F2
        ''',
        a_legacy=LegacyDefinition(name='x_fplo_t_dft_plus_u_species_subshell_F2'))

    x_fplo_t_dft_plus_u_species_subshell_F4 = Quantity(
        type=np.dtype(np.float64),
        shape=[],
        description='''
        Temporary storage for FPLO per species/(n,l)subshell DFT+U F4
        ''',
        a_legacy=LegacyDefinition(name='x_fplo_t_dft_plus_u_species_subshell_F4'))

    x_fplo_t_dft_plus_u_species_subshell_F6 = Quantity(
        type=np.dtype(np.float64),
        shape=[],
        description='''
        Temporary storage for FPLO per species/(n,l)subshell DFT+U F6
        ''',
        a_legacy=LegacyDefinition(name='x_fplo_t_dft_plus_u_species_subshell_F6'))

    x_fplo_t_dft_plus_u_species_subshell_U = Quantity(
        type=np.dtype(np.float64),
        shape=[],
        description='''
        Temporary storage for FPLO per species/(n,l)subshell DFT+U U
        ''',
        a_legacy=LegacyDefinition(name='x_fplo_t_dft_plus_u_species_subshell_U'))

    x_fplo_t_dft_plus_u_species_subshell_J = Quantity(
        type=np.dtype(np.float64),
        shape=[],
        description='''
        Temporary storage for FPLO per species/(n,l)subshell DFT+U J
        ''',
        a_legacy=LegacyDefinition(name='x_fplo_t_dft_plus_u_species_subshell_J'))

    x_fplo_t_dft_plus_u_site_index = Quantity(
        type=np.dtype(np.int32),
        shape=[],
        description='''
        Temporary storage for FPLO per site DFT+U index
        ''',
        a_legacy=LegacyDefinition(name='x_fplo_t_dft_plus_u_site_index'))

    x_fplo_t_dft_plus_u_site_element = Quantity(
        type=str,
        shape=[],
        description='''
        Temporary storage for FPLO per site DFT+U element
        ''',
        a_legacy=LegacyDefinition(name='x_fplo_t_dft_plus_u_site_element'))

    x_fplo_t_dft_plus_u_site_species = Quantity(
        type=np.dtype(np.int32),
        shape=[],
        description='''
        Temporary storage for FPLO per site DFT+U species
        ''',
        a_legacy=LegacyDefinition(name='x_fplo_t_dft_plus_u_site_species'))

    x_fplo_t_dft_plus_u_site_subshell = Quantity(
        type=str,
        shape=[],
        description='''
        Temporary storage for FPLO per site DFT+U (n,l)subshell
        ''',
        a_legacy=LegacyDefinition(name='x_fplo_t_dft_plus_u_site_subshell'))

    x_fplo_t_dft_plus_u_site_ubi1 = Quantity(
        type=np.dtype(np.int32),
        shape=[],
        description='''
        Temporary storage for FPLO per site DFT+U ubi1
        ''',
        a_legacy=LegacyDefinition(name='x_fplo_t_dft_plus_u_site_ubi1'))

    x_fplo_t_dft_plus_u_site_ubi2 = Quantity(
        type=np.dtype(np.int32),
        shape=[],
        description='''
        Temporary storage for FPLO per site DFT+U ubi2
        ''',
        a_legacy=LegacyDefinition(name='x_fplo_t_dft_plus_u_site_ubi2'))


class section_scf_iteration(public.section_scf_iteration):

    m_def = Section(validate=False, extends_base_section=True, a_legacy=LegacyDefinition(name='section_scf_iteration'))

    x_fplo_t_energy_reference_fermi_iteration = Quantity(
        type=np.dtype(np.float64),
        shape=[],
        unit='joule',
        description='''
        Temporary storage for FPLO Fermi energy in iteration
        ''',
        categories=[public.energy_type_reference, public.energy_value],
        a_legacy=LegacyDefinition(name='x_fplo_t_energy_reference_fermi_iteration'))


m_package.__init_metainfo__()
