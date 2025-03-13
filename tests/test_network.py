import pytest
from tools4rdf.network.ontology import read_ontology
from rdflib import Graph

def test_network():
    onto = read_ontology()
    kg = Graph()
    kg.parse("tests/triples", format="turtle")
    df = onto.query(kg, onto.terms.cmso.AtomicScaleSample, [onto.terms.cmso.hasSpaceGroupSymbol, onto.terms.cmso.hasNumberOfAtoms==4])
    assert len(df) == 14