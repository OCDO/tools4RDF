import os
from tools4rdf.network.network import OntologyNetwork


def read_ontology():
    """
    Read in ontologies and perform necessary operations.

    Returns
    -------
    combo: OntologyNetwork, Combined ontology network.
    """
    # read in ontologies
    file_location = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    cmso = OntologyNetwork(os.path.join(file_location, "data/cmso.owl"))
    # return
    return cmso
