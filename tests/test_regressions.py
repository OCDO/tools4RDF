"""
Regression tests for defects found in the 2026-09 audit.
"""

import pytest
from rdflib import Graph, Namespace, RDF, RDFS, OWL, XSD, BNode, Literal
from rdflib.collection import Collection
from rdflib.plugins.sparql import prepareQuery

from tools4rdf.network.parser import OntoParser
from tools4rdf.network.network import OntologyNetworkBase
from tools4rdf.network.ontology import read_ontology
from tools4rdf.network.term import OntoTerm

EX = Namespace("http://example.org/o#")


def make_graph(classes=(), triples=()):
    g = Graph()
    g.bind("ex", EX)
    for c in classes:
        g.add((EX[c], RDF.type, OWL.Class))
    for t in triples:
        g.add(t)
    return g


def add_union(g, subclass, members):
    bn = BNode()
    lst = BNode()
    Collection(g, lst, [EX[m] for m in members])
    g.add((bn, RDF.type, OWL.Class))
    g.add((bn, OWL.unionOf, lst))
    g.add((EX[subclass], RDFS.subClassOf, bn))


def test_unions_do_not_leak_between_mappings():
    g = make_graph("ABCDEF")
    add_union(g, "E", ["A", "B"])
    add_union(g, "F", ["C", "D"])
    parser = OntoParser(g)
    items = sorted(sorted(v["items"]) for v in parser.mappings.values())
    assert items == [["ex:A", "ex:B"], ["ex:C", "ex:D"]]
    assert parser.attributes["class"]["ex:A"].subclasses == ["ex:E"]


def test_unions_do_not_leak_between_parsers():
    g = make_graph("ABE")
    add_union(g, "E", ["A", "B"])
    OntoParser(g).attributes
    # a second, unrelated ontology must still parse
    onto = read_ontology()
    assert "cmso:AtomicScaleSample" in onto.attributes["class"]


def test_nested_class_expression_as_superclass():
    g = make_graph("ABC")
    inner = BNode()
    inner_list = BNode()
    Collection(g, inner_list, [EX.A, EX.B])
    g.add((inner, RDF.type, OWL.Class))
    g.add((inner, OWL.intersectionOf, inner_list))
    outer = BNode()
    outer_list = BNode()
    Collection(g, outer_list, [inner, EX.B])
    g.add((outer, RDF.type, OWL.Class))
    g.add((outer, OWL.unionOf, outer_list))
    g.add((EX.C, RDFS.subClassOf, outer))
    parser = OntoParser(g)
    assert "ex:C" in parser.attributes["class"]["ex:B"].subclasses


def test_superclass_from_unloaded_ontology():
    ext = Namespace("http://external.org/")
    g = make_graph("AC")
    bn = BNode()
    lst = BNode()
    Collection(g, lst, [EX.A, ext.Z])
    g.add((bn, RDF.type, OWL.Class))
    g.add((bn, OWL.unionOf, lst))
    g.add((EX.C, RDFS.subClassOf, bn))
    parser = OntoParser(g)
    assert "ex:C" in parser.attributes["class"]["ex:A"].subclasses


def test_named_individual_of_unloaded_class():
    ext = Namespace("http://external.org/")
    g = make_graph("A")
    g.add((EX.ind, RDF.type, OWL.NamedIndividual))
    g.add((EX.ind, RDF.type, ext.Z))
    g.add((EX.ind2, RDF.type, OWL.NamedIndividual))
    g.add((EX.ind2, RDF.type, EX.A))
    parser = OntoParser(g)
    assert "ex:ind" in parser.attributes["class"]
    assert parser.attributes["class"]["ex:A"].named_individuals == ["ex:ind2"]


def object_property_network():
    g = make_graph(
        "ABC",
        [
            (EX.p, RDF.type, OWL.ObjectProperty),
            (EX.p, RDFS.domain, EX.A),
            (EX.p, RDFS.range, EX.B),
        ],
    )
    for d in ["x", "y"]:
        g.add((EX[d], RDF.type, OWL.DatatypeProperty))
        g.add((EX[d], RDFS.domain, EX.A))
        g.add((EX[d], RDFS.range, XSD.float))
    return OntologyNetworkBase(OntoParser(g))


def test_object_property_source_with_several_destinations():
    net = object_property_network()
    t = net.terms.ex
    query = net.create_query(t.p, [t.x, t.y])
    assert "?A ex:p ?p ." in query
    assert "?A ex:x ?xvalue ." in query
    assert "?A ex:y ?yvalue ." in query
    Graph().query(query)


def test_object_property_already_in_destinations():
    net = object_property_network()
    t = net.terms.ex
    query = net.create_query(t.p, [t.p, t.x])
    assert query.count("ex:p") == 1


def test_filter_declares_xsd_prefix():
    onto = read_ontology()
    c = onto.terms.cmso
    query = onto.create_query(c.AtomicScaleSample, [c.hasNumberOfAtoms == 4])
    assert "PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>" in query
    # must parse without rdflib's default namespace bindings
    prepareQuery(query, initNs={})


def test_term_label_is_kept():
    term = OntoTerm(uri="http://example.org/o#A", label="my label")
    assert term.label == "my label"


def test_parser_reads_labels():
    g = make_graph(
        "AB",
        [
            (EX.A, RDFS.label, Literal("Klasse A", lang="de")),
            (EX.A, RDFS.label, Literal("class A", lang="en")),
        ],
    )
    parser = OntoParser(g)
    assert parser.attributes["class"]["ex:A"].label == "class A"
    assert parser.attributes["class"]["ex:B"].label is None


def test_and_or_methods_return_combined_term():
    onto = read_ontology()
    c = onto.terms.cmso
    combined = (c.hasNumberOfAtoms > 1).and_(c.hasNumberOfAtoms < 10)
    assert "&&" in combined._condition
    combined = (c.hasNumberOfAtoms > 1).or_(c.hasNumberOfAtoms < 10)
    assert "||" in combined._condition


def test_terms_are_hashable_and_comparable():
    onto = read_ontology()
    c = onto.terms.cmso
    assert len({c.AtomicScaleSample, c.AtomicScaleSample, c.hasNumberOfAtoms}) == 2
    assert c.AtomicScaleSample != "cmso:AtomicScaleSample"
    assert not (c.AtomicScaleSample == "anything")
    # data properties compared to terms do not produce conditions
    assert (c.hasNumberOfAtoms == c.hasNumberOfAtoms) is True
    assert c.hasNumberOfAtoms not in [c.hasVolume]


def data_property_network(range_):
    triples = [
        (EX.v, RDF.type, OWL.DatatypeProperty),
        (EX.v, RDFS.domain, EX.A),
    ]
    if range_ is not None:
        triples.append((EX.v, RDFS.range, range_))
    return OntologyNetworkBase(OntoParser(make_graph("A", triples)))


def run_filter(range_, stored, value):
    net = data_property_network(range_)
    kg = Graph()
    kg.add((EX.i, RDF.type, EX.A))
    kg.add((EX.i, EX.v, stored))
    query = net.create_query(net.terms.ex.A, [net.terms.ex.v == value])
    return query, len(kg.query(query))


def test_filter_string_with_quotes():
    query, rows = run_filter(XSD.string, Literal('P"1'), 'P"1')
    assert rows == 1


def test_filter_boolean_uses_canonical_lexical_form():
    query, rows = run_filter(XSD.boolean, Literal(True), True)
    assert '"true"^^xsd:boolean' in query
    assert rows == 1


def test_filter_rdfs_literal_range():
    query, rows = run_filter(RDFS.Literal, Literal("x"), "x")
    assert "xsd:Literal" not in query
    assert rows == 1


def test_filter_without_range():
    query, rows = run_filter(None, Literal(3), 3)
    assert rows == 1


def test_hyphenated_intermediate_class():
    g = make_graph(
        ["A", "Twin-like"],
        [
            (EX.p, RDF.type, OWL.ObjectProperty),
            (EX.p, RDFS.domain, EX.A),
            (EX.p, RDFS.range, EX["Twin-like"]),
            (EX.x, RDF.type, OWL.DatatypeProperty),
            (EX.x, RDFS.domain, EX["Twin-like"]),
            (EX.x, RDFS.range, XSD.float),
        ],
    )
    net = OntologyNetworkBase(OntoParser(g))
    kg = Graph()
    kg.add((EX.a, RDF.type, EX.A))
    kg.add((EX.a, EX.p, EX.t))
    kg.add((EX.t, EX.x, Literal(1.0)))
    df = net.query(kg, net.terms.ex.A, [net.terms.ex.x])
    assert len(df) == 1


def test_every_source_keeps_the_filter():
    g = make_graph(
        "AB",
        [
            (EX.x, RDF.type, OWL.DatatypeProperty),
            (EX.x, RDFS.domain, EX.A),
            (EX.x, RDFS.domain, EX.B),
            (EX.x, RDFS.range, XSD.float),
        ],
    )
    net = OntologyNetworkBase(OntoParser(g))
    t = net.terms.ex
    queries = net.create_query([t.A, t.B], [t.x > 3])
    assert len(queries) == 2
    assert all("FILTER" in q for q in queries)


def test_create_query_does_not_mutate_shared_terms():
    onto = read_ontology()
    c = onto.terms.cmso
    with pytest.raises(Exception):
        # no path exists, so this raises half-way through
        onto.create_query(
            c.AtomicScaleSample, [[c.hasSpaceGroupSymbol, c.hasNumberOfAtoms]]
        )
    assert onto.terms.cmso.hasNumberOfAtoms._parents == []
    onto.create_query(c.AtomicScaleSample, [[c.Material, c.CrystalStructure]])
    assert onto.terms.cmso.CrystalStructure._parents == []


def test_add_path_creates_edges_for_class_and_subclasses():
    g = make_graph(
        "ABC",
        [
            (EX.C, RDFS.subClassOf, EX.A),
            (EX.p, RDF.type, OWL.ObjectProperty),
        ],
    )
    net = OntologyNetworkBase(OntoParser(g))
    net.add_path(("ex:A", "ex:p", "ex:B"))
    assert net.g.has_edge("ex:A", "ex:p")
    assert net.g.has_edge("ex:C", "ex:p")
    assert net.g.has_edge("ex:p", "ex:B")
    assert "?A ex:p ?p ." in net.create_query(net.terms.ex.A, [net.terms.ex.p])


def test_add_path_rdfs_label_like_atomrdf():
    net = OntologyNetworkBase(OntoParser(make_graph("A")))
    net.add_namespace("rdfs", "http://www.w3.org/2000/01/rdf-schema#")
    net.add_term(
        "http://www.w3.org/2000/01/rdf-schema#label",
        "data_property",
        rn=["str"],
    )
    net.add_path(("ex:A", "rdfs:label", "string"))
    kg = Graph()
    kg.add((EX.a, RDF.type, EX.A))
    kg.add((EX.a, RDFS.label, Literal("name")))
    df = net.query(kg, net.terms.ex.A, [net.terms.rdfs.label == "name"])
    assert len(df) == 1


def test_add_path_survives_combining_networks():
    net = OntologyNetworkBase(OntoParser(make_graph("AB", [(EX.p, RDF.type, OWL.ObjectProperty)])))
    net.add_path(("ex:A", "ex:p", "ex:B"))
    other = OntologyNetworkBase(OntoParser(make_graph("D")))
    combined = net + other
    assert combined.g.has_edge("ex:A", "ex:p")


def test_add_path_rejects_unknown_property():
    net = OntologyNetworkBase(OntoParser(make_graph("AB")))
    with pytest.raises(ValueError):
        net.add_path(("ex:A", "ex:missing", "ex:B"))


def test_most_specific_namespace_wins():
    g = Graph()
    g.bind("base", Namespace("http://example.org/"))
    g.bind("ex", EX)
    g.add((EX.A, RDF.type, OWL.Class))
    parser = OntoParser(g)
    assert "ex:A" in parser.attributes["class"]
    assert "base:A" not in parser.attributes["class"]


def test_same_local_name_in_two_namespaces():
    Y = Namespace("http://other.org/y#")
    g = make_graph(
        "AB",
        [
            (EX.hasB, RDF.type, OWL.ObjectProperty),
            (EX.hasB, RDFS.domain, EX.A),
            (EX.hasB, RDFS.range, EX.B),
            (EX.value, RDFS.domain, EX.A),
            (Y.value, RDFS.domain, EX.B),
        ],
    )
    g.bind("y", Y)
    for ns in (EX, Y):
        g.add((ns.value, RDF.type, OWL.DatatypeProperty))
        g.add((ns.value, RDFS.range, XSD.float))
    net = OntologyNetworkBase(OntoParser(g))
    kg = Graph()
    kg.add((EX.a, RDF.type, EX.A))
    kg.add((EX.a, EX.hasB, EX.b))
    kg.add((EX.a, EX.value, Literal(1.0)))
    kg.add((EX.b, Y.value, Literal(2.0)))
    df = net.query(kg, net.terms.ex.A, [net.terms.ex.value, net.terms.y.value > 1])
    assert list(df.columns) == ["A", "ex_valuevalue", "y_valuevalue"]
    assert len(df) == 1
    df = net.query(kg, net.terms.ex.A, [net.terms.ex.value, net.terms.y.value > 5])
    assert len(df) == 0
