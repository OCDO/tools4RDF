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
    file_location = os.path.dirname(__file__).split("/")
    file_location = "/".join(file_location[:-1])

    cmso = OntologyNetwork(
        os.path.join(file_location, "data/cmso.owl")
    )  # b7c8f3544d16d0ec9a9aace682da0e6abba1c57f
    pldo = OntologyNetwork(
        os.path.join(file_location, "data/pldo.owl")
    )  # 688ce36a3e6520a6e280bb248789c231d3c36f25
    podo = OntologyNetwork(
        os.path.join(file_location, "data/podo.owl")
    )  # 6a74d511c5b78042e1cb7a6e76e948fa56de598e
    asmo = OntologyNetwork(
        os.path.join(file_location, "data/asmo.owl")
    )  # 688ce36a3e6520a6e280bb248789c231d3c36f25
    ldo = OntologyNetwork(
        os.path.join(file_location, "data/ldo.owl")
    )  # e23fa9930351787e701347878a3e1a0e3924d084

    # combine them
    combo = cmso + pldo + podo + asmo + ldo

    # return
    return combo
