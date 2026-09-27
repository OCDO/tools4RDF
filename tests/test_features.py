"""
Tests for query features: several filters, optional destinations and
Python values in results.
"""

import pytest
from rdflib import Graph, Namespace, RDF, RDFS, OWL, XSD, Literal

from tools4rdf.network.parser import OntoParser
from tools4rdf.network.network import OntologyNetworkBase

EX = Namespace("http://example.org/o#")


@pytest.fixture
def net():
    """
    Sample --hasCell--> Cell ; Sample has natoms (int), label (string);
    Cell has volume (float).
    """
    g = Graph()
    g.bind("ex", EX)
    for c in ["Sample", "Cell"]:
        g.add((EX[c], RDF.type, OWL.Class))
    g.add((EX.hasCell, RDF.type, OWL.ObjectProperty))
    g.add((EX.hasCell, RDFS.domain, EX.Sample))
    g.add((EX.hasCell, RDFS.range, EX.Cell))
    for prop, domain, rng in [
        ("natoms", "Sample", XSD.integer),
        ("name", "Sample", XSD.string),
        ("volume", "Cell", XSD.float),
    ]:
        g.add((EX[prop], RDF.type, OWL.DatatypeProperty))
        g.add((EX[prop], RDFS.domain, EX[domain]))
        g.add((EX[prop], RDFS.range, rng))
    return OntologyNetworkBase(OntoParser(g))


@pytest.fixture
def kg():
    """s1: 4 atoms, volume 10, name 'fcc'; s2: 100 atoms, volume 50, no name;
    s3: 200 atoms, no cell, name 'bcc'."""
    g = Graph()
    for s, natoms in [("s1", 4), ("s2", 100), ("s3", 200)]:
        g.add((EX[s], RDF.type, EX.Sample))
        g.add((EX[s], EX.natoms, Literal(natoms)))
    for s, cell, volume in [("s1", "c1", 10.0), ("s2", "c2", 50.0)]:
        g.add((EX[s], EX.hasCell, EX[cell]))
        g.add((EX[cell], RDF.type, EX.Cell))
        g.add((EX[cell], EX.volume, Literal(volume, datatype=XSD.float)))
    g.add((EX.s1, EX.name, Literal("fcc")))
    g.add((EX.s3, EX.name, Literal("bcc")))
    return g


def samples(df):
    return sorted(str(x).split("#")[-1] for x in df["Sample"])


def test_two_filters_on_different_properties(net, kg):
    t = net.terms.ex
    df = net.query(kg, t.Sample, [t.natoms > 50, t.volume < 60])
    assert samples(df) == ["s2"]


def test_range_filter_on_one_property(net, kg):
    t = net.terms.ex
    query = net.create_query(t.Sample, [t.natoms > 50, t.natoms < 150])
    select = [line for line in query.splitlines() if line.startswith("SELECT")][0]
    assert select.count("?natomsvalue") == 1
    assert samples(net.query(kg, t.Sample, [t.natoms > 50, t.natoms < 150])) == ["s2"]


def test_or_condition_is_not_narrowed_by_its_operands(net, kg):
    t = net.terms.ex
    df = net.query(kg, t.Sample, [(t.natoms < 10) | (t.volume > 40)])
    assert samples(df) == ["s1", "s2"]


def test_and_condition_combined_with_a_separate_filter(net, kg):
    t = net.terms.ex
    df = net.query(kg, t.Sample, [(t.natoms > 1) & (t.volume > 1), t.natoms < 50])
    assert samples(df) == ["s1"]
