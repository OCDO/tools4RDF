"""
Regression tests for defects found in the 2026-09 audit.
"""

import pytest
from rdflib import Graph, Namespace, RDF, RDFS, OWL, BNode
from rdflib.collection import Collection

from tools4rdf.network.parser import OntoParser
from tools4rdf.network.ontology import read_ontology

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
