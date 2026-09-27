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
