import numpy as np
import spglib

# DATADICT properties
#------------------------------------------
bravais_lattice_dict = {
    "l12": "https://www.wikidata.org/wiki/Q3006714",
    "b2": "https://www.wikidata.org/wiki/Q851536",
    "diamond": "https://www.wikidata.org/wiki/Q3006714",
    "hcp": "https://www.wikidata.org/wiki/Q663314",
    "a15": "a15",
    "bcc": "https://www.wikidata.org/wiki/Q851536",
    "fcc": "https://www.wikidata.org/wiki/Q3006714",
}

# SIMCELL properties
#--------------------------------------------
def get_chemical_composition(system):
    return system.composition

def get_cell_volume(system):
    return system.volume

def get_number_of_atoms(system):
    return system.natoms

def get_simulation_cell_length(system):
    return system.box_dimensions

def get_simulation_cell_vector(system):
    return system.box

def get_simulation_cell_angle(system):
    return [_get_angle(system.box[0], system.box[1]),
            _get_angle(system.box[1], system.box[2]),
            _get_angle(system.box[2], system.box[0])]

# LATTICE properties
#--------------------------------------------

def get_lattice_angle(system):
    if system._structure_dict is None:
        return None

    return [_get_angle(system._structure_dict["box"][0], system._structure_dict["box"][1]),
            _get_angle(system._structure_dict["box"][1], system._structure_dict["box"][2]),
            _get_angle(system._structure_dict["box"][2], system._structure_dict["box"][0])]

def get_lattice_parameter(system):
    if system.atoms._lattice_constant is None:
        return [None, None, None]
    else:
        if system._structure_dict is not None:
            return [np.linalg.norm(system._structure_dict["box"][0])*system.atoms._lattice_constant,
                    np.linalg.norm(system._structure_dict["box"][1])*system.atoms._lattice_constant,
                    np.linalg.norm(system._structure_dict["box"][2])*system.atoms._lattice_constant]
        else:
            return [system.atoms._lattice_constant, 
                    system.atoms._lattice_constant, 
                    system.atoms._lattice_constant]

def get_crystal_structure_name(system):
    if system._structure_dict is None:
        return None
    return system.atoms._lattice

def get_bravais_lattice(system):
    if system._structure_dict is None:
        return None
    if system.atoms._lattice in bravais_lattice_dict.keys():
        return bravais_lattice_dict[system.atoms._lattice]
    return None

def get_basis_positions(system):
    if system._structure_dict is None:
        return None
    return system._structure_dict["positions"]

def get_basis_occupancy(system):
    if system._structure_dict is None:
        return None
    occ_numbers = system._structure_dict['species']
    tdict = system.atoms._type_dict
    vals = [val for key, val in tdict.items()]
    
    if vals[0] is not None:
        occ_numbers = [tdict[x] for x in occ_numbers]
    return occ_numbers

def get_lattice_vectors(system):
    if system._structure_dict is None:
        return None
    return system._structure_dict["box"]

def get_spacegroup_symbol(system):
    if system._structure_dict is None:
        return None
    results = _get_symmetry_dict(system)
    return results["international"]

def get_spacegroup_number(system):
    if system._structure_dict is None:
        return None
    results = _get_symmetry_dict(system)
    return results["number"]

# ATOM attributes
#--------------------------------------------
def get_position(system):
    return system.atoms.position

def get_species(system):
    return system.atoms.species



# SUPPORT functions
#--------------------------------------------
def _get_angle(vec1, vec2):
    """
    Get angle between two vectors in degrees
    
    Parameters
    ----------
    vec1: list
        first vector
    
    vec2: list
        second vector
    
    Returns
    -------
    angle: float
        angle in degrees
    
    Notes
    -----
    Angle is rounded to two decimal points
    
    """
    return np.round(np.arccos(np.dot(vec1, vec2)/(np.linalg.norm(vec1)*np.linalg.norm(vec2)))*180/np.pi, decimals=2)

def _get_symmetry_dict(system):
    box = get_lattice_vector(system)
    direct_coordinates = get_basis_positions(system)
    atom_types = system._structure_dict['species']

    results = spglib.get_symmetry_dataset((box,
    direct_coordinates, atom_types))
    return results["international"], results["number"]    
