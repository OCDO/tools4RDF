import pytest
from tools4rdf.network.ontology import read_ontology
from rdflib import Graph

def test_network():
    onto = read_ontology()
    kg = Graph()
    kg.parse("tests/triples", format="turtle")
    df = onto.query(kg, onto.terms.cmso.AtomicScaleSample, [onto.terms.cmso.hasSpaceGroupSymbol, onto.terms.cmso.hasNumberOfAtoms==4])
    assert len(df) == 14

def test_owlThing():
    onto = read_ontology()
    query = (onto.create_query(onto.terms.cmso.AtomicScaleSample,onto.terms.cmso.hasAltName@onto.terms.cmso.CrystalStructure))
    assert "CrystalStructure_hasAltNamevalue" in query