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


def test_optional_keeps_rows_without_the_value(net, kg):
    t = net.terms.ex
    df = net.query(kg, t.Sample, [t.natoms, t.name.optional])
    assert samples(df) == ["s1", "s2", "s3"]
    names = {str(s).split("#")[-1]: n for s, n in zip(df["Sample"], df["namevalue"])}
    assert str(names["s1"]) == "fcc"
    assert names["s2"] is None


def test_required_destination_still_filters_rows(net, kg):
    t = net.terms.ex
    # s3 has no cell, so it drops out; s2 has no name but is kept
    df = net.query(kg, t.Sample, [t.volume, t.name.optional])
    assert samples(df) == ["s1", "s2"]


def test_optional_path_through_another_class(net, kg):
    t = net.terms.ex
    query = net.create_query(t.Sample, [t.natoms, t.volume.optional])
    optional_block = query.split("OPTIONAL {")[1].split("}")[0]
    assert "ex:hasCell" in optional_block
    assert "ex:volume" in optional_block
    df = net.query(kg, t.Sample, [t.natoms, t.volume.optional])
    assert samples(df) == ["s1", "s2", "s3"]


def test_condition_on_optional_stays_inside_its_block(net, kg):
    t = net.terms.ex
    query = net.create_query(t.Sample, [t.natoms, (t.volume > 20).optional])
    assert "FILTER" in query.split("OPTIONAL {")[1].split("}")[0]
    df = net.query(kg, t.Sample, [t.natoms, (t.volume > 20).optional])
    # every sample is kept; only s2 has a volume above 20
    assert samples(df) == ["s1", "s2", "s3"]
    volumes = [v for v in df["volumevalue"] if v is not None]
    assert [float(v) for v in volumes] == [50.0]


def test_optional_query_parses_without_default_prefixes(net):
    from rdflib.plugins.sparql import prepareQuery

    t = net.terms.ex
    query = net.create_query(t.Sample, [t.natoms > 1, (t.volume > 20).optional])
    prepareQuery(query, initNs={})


def test_optional_does_not_mutate_shared_term(net):
    t = net.terms.ex
    t.name.optional
    assert net.terms.ex.name._optional is False


def test_optional_last_step_of_stepped_query(net, kg):
    t = net.terms.ex
    df = net.query(kg, t.Sample, [t.natoms, [t.hasCell, t.volume.optional]])
    assert samples(df) == ["s1", "s2", "s3"]


def test_python_values_gives_numeric_columns(net, kg):
    t = net.terms.ex
    df = net.query(kg, t.Sample, [t.natoms, t.volume], python_values=True)
    assert df["natomsvalue"].dtype.kind == "i"
    assert df["volumevalue"].dtype.kind == "f"
    assert sorted(df["natomsvalue"]) == [4, 100]
    assert all(isinstance(s, str) for s in df["Sample"])
    assert list(df.index) == list(range(len(df)))


def test_python_values_with_missing_optional_values(net, kg):
    t = net.terms.ex
    df = net.query(
        kg, t.Sample, [t.natoms, t.volume.optional, t.name.optional], python_values=True
    )
    assert df["volumevalue"].dtype.kind == "f"
    assert df["volumevalue"].isna().sum() == 1
    names = dict(zip(df["Sample"], df["namevalue"]))
    assert names[str(EX.s1)] == "fcc"
    assert names[str(EX.s2)] is None


def test_default_keeps_rdflib_terms(net, kg):
    t = net.terms.ex
    df = net.query(kg, t.Sample, [t.natoms])
    assert all(isinstance(v, Literal) for v in df["natomsvalue"])
