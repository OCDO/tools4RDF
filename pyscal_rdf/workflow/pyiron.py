"""
Wrappers for pyiron jobs
"""
import os
from functools import partial, update_wrapper
import pyscal_rdf.workflow.workflow as wf
from pyscal_rdf.structure import _make_crystal
from pyscal_rdf.structure import System
from pyscal3.core import structure_dict, element_dict


def _check_if_job_is_valid(job):
    valid_jobs = ['Lammps', ]
    
    if not type(job).__name__ in valid_jobs:
        raise TypeError('These type of pyiron Job is not currently supported')


def _add_structures(kg, job):
    initial_pyiron_structure = job.structure
    final_pyiron_structure = job.get_structure(frame=-1)
    initial_pyscal_structure =  System.read.ase(initial_pyiron_structure)

    initial_sample_id = None
    if 'sample_id' in initial_pyiron_structure.info.keys():
        if not initial_pyiron_structure.info['sample_id'] in kg.samples:
            kg.add_structure(initial_pyscal_structure)
        else:
            initial_sample_id = initial_pyiron_structure.info['sample_id']
    else:
        kg.add_structure(initial_pyscal_structure)

    if initial_sample_id is None:
        initial_sample_id = initial_pyscal_structure.sample

    #add final structure
    final_pyscal_structure = System.read.ase(final_pyiron_structure, graph=kg)
    final_sample_id = final_pyscal_structure.sample

    #now we do rthe transfer
    return final_sample_id


def _identify_method(job):
    job_dict = job.input.to_dict()
    input_dict = {job_dict['control_inp/data_dict']['Parameter'][x]:job_dict['control_inp/data_dict']['Value'][x] for x in range(len(job_dict['control_inp/data_dict']['Parameter']))}
    dof = []
    temp = None
    press = None
    md_method = None
    ensemble = None

    if 'min_style' in input_dict.keys():
        dof.append('AtomicPosition')
        dof.append('CellVolume')
        md_method = 'MolecularStatics'

    elif 'nve' in input_dict['fix___ensemble']:
        if int(input_dict['run']) == 0:
            method = 'static'
            md_method = 'MolecularStatics'
            ensemble = 'NVE'

        elif int(input_dict['run']) > 0:
            method = 'md_nve'
            dof.append('AtomicPosition')
            md_method = 'MolecularDynamics'
            ensemble = 'NVE'


    elif 'nvt' in input_dict['fix___ensemble']:
        method = 'md_nvt'
        raw = input_dict['fix___ensemble'].split()
        temp = float(raw[3])
        dof.append('AtomicPosition')
        md_method = 'MolecularDynamics'
        ensemble = 'NVT'

    elif 'npt' in input_dict['fix___ensemble']:
        dof.append('AtomicPosition')
        dof.append('CellVolume')
        if 'aniso' in input_dict['fix___ensemble']:
            method = 'md_npt_aniso'
            dof.append('CellShape')
        else:
            method = 'md_npt_iso'
        md_method = 'MolecularDynamics'        
        raw = input_dict['fix___ensemble'].split()
        temp = float(raw[3])
        press = float(raw[7])
        ensemble = 'NPT'


    mdict = {}
    mdict['method'] = md_method
    mdict['temperature'] = temp
    mdict['pressure'] = press
    mdict['dof'] = dof
    mdict['ensemble'] = ensemble
    mdict['id'] = job.id

    return mdict


def _add_method(kg, job):
    mdict = _identify_method(job)
    activity_id = wf.add_method(kg, mdict)
    return activity_id

def add_mappings(kg, job):
    final_sample_id = _add_structures(kg, job)
    final_sample_id = wf.add_derived_structure(kg, initial_sample_id, final_sample_id)

    activity_id = _add_method(kg, job)
    


def update_project(pr, kg):
    """
    Update project to add extra creator functions
    """

    try:
        from pyiron_base import Creator, PyironFactory
        from pyiron_atomistics.atomistics.structure.atoms import ase_to_pyiron, pyiron_to_ase
        import pyiron_atomistics.atomistics.structure.factory as sf
    except ImportError:
        raise ImportError('Please install pyiron_base and pyiron_atomistics')

    class AnnotatedStructureFactory:
        def __init__(self, graph):
            self._graph = graph

        def bulk(self, 
            element,
            repetitions=None, 
            crystalstructure=None,
            a=None,
            covera=None,
            cubic=True,
            graph=None):

            if crystalstructure is None:
                crystalstructure = element_dict[element]['structure']
                if a is None:
                    a = element_dict[element]['lattice_constant']
        
            struct = _make_crystal(crystalstructure,
                repetitions=repetitions,
                lattice_constant=a,
                ca_ratio = covera,
                element = element,
                primitive = not cubic,
                graph=self._graph,
                )
            
            ase_structure = struct.write.ase()
            pyiron_structure = ase_to_pyiron(ase_structure)
            pyiron_structure.info['sample_id'] = struct.sample
            return pyiron_structure

        def grain_boundary(self,
            element,
            axis,
            sigma,
            gb_plane,
            repetitions = (1,1,1),
            crystalstructure=None,
            a=1,
            overlap=0.0,
            graph=None,
            ):

            struct = self._graph._annotated_make_grain_boundary(axis,
                sigma,
                gb_plane,
                structure = crystalstructure,
                element=element,
                lattice_constant=a,
                repetitions=repetitions,
                overlap=overlap,
                graph=self._graph)

            ase_structure = struct.write.ase()
            pyiron_structure = ase_to_pyiron(ase_structure)
            pyiron_structure.info['sample_id'] = struct.sample
            return pyiron_structure


    class StructureFactory(sf.StructureFactory):
        def __init__(self, graph):
            super().__init__()
            self._annotated_structure = AnnotatedStructureFactory(graph)

        @property
        def annotated_structure(self):
            return self._annotated_structure

    
    class StructureCreator(Creator):
        def __init__(self, project):
            super().__init__(project)
            self._structure = StructureFactory(project.graph)

        @property
        def structure(self):
            return self._structure
    
    pr.graph = kg
    pr._creator = StructureCreator(pr)
     