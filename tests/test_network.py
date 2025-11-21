import pytest
from tools4rdf.network.ontology import read_ontology
from tools4rdf.network.network import (
    Network,
    OntologyNetwork,
    OntologyNetworkBase,
    _replace_name,
    _strip_name,
)
from tools4rdf.network.parser import OntoParser
from tools4rdf.network.term import OntoTerm
from rdflib import Graph, Namespace, RDF, RDFS, OWL, URIRef


def test_network():
    onto = read_ontology()
    kg = Graph()
    kg.parse("tests/triples", format="turtle")
    df = onto.query(
        kg,
        onto.terms.cmso.AtomicScaleSample,
        [onto.terms.cmso.hasSpaceGroupSymbol, onto.terms.cmso.hasNumberOfAtoms == 4],
    )
    assert len(df) == 14


def test_owlThing():
    onto = read_ontology()
    query = onto.create_query(
        onto.terms.cmso.AtomicScaleSample,
        [[onto.terms.cmso.CrystalStructure, onto.terms.cmso.hasAltName]],
    )
    assert "CrystalStructure_hasAltNamevalue" in query


@pytest.fixture
def simple_onto():
    g = Graph()
    ex = Namespace("http://example.org/ontology#")
    g.bind("ex", ex)
    g.add((ex.Pizza, RDF.type, OWL.Class))
    g.add((ex.Food, RDF.type, OWL.Class))
    g.add((ex.Person, RDF.type, OWL.Class))
    g.add((ex.Pizza, RDFS.subClassOf, ex.Food))
    g.add((ex.hasTopping, RDF.type, OWL.ObjectProperty))
    g.add((ex.hasTopping, RDFS.domain, ex.Pizza))
    g.add((ex.hasTopping, RDFS.range, ex.Food))
    g.add((ex.hasPrice, RDF.type, OWL.DatatypeProperty))
    g.add((ex.hasPrice, RDFS.domain, ex.Pizza))
    return OntoParser(g)


@pytest.fixture
def network_fixture(simple_onto):
    return Network(simple_onto)


def test_replace_name():
    assert _replace_name("ex:Pizza") == "ex.Pizza"
    assert _replace_name("simple") == "simple"


def test_strip_name():
    assert _strip_name("ex:Pizza") == "Pizza"
    assert _strip_name("Pizza") == "Pizza"


def test_network_init(simple_onto):
    network = Network(simple_onto)
    assert network.terms is not None
    assert network.g is not None
    assert network.namespaces is not None
    assert network.extra_namespaces is not None


def test_network_draw(network_fixture):
    dot = network_fixture.draw()
    assert dot is not None


def test_network_draw_custom_style(network_fixture):
    style = {
        "class": {"shape": "circle"},
        "object_property": {"shape": "diamond"},
        "data_property": {"shape": "box"},
        "literal": {"shape": "parallelogram"},
    }
    dot = network_fixture.draw(styledict=style)
    assert dot is not None


def test_get_shortest_path_simple(network_fixture):
    source = network_fixture.terms.ex.Pizza
    target = network_fixture.terms.ex.hasTopping
    paths = network_fixture._get_shortest_path(source, target, num_paths=1)
    assert len(paths) > 0
    assert paths[0][0] == source.variable_name


def test_get_shortest_path_multiple_paths(network_fixture):
    source = network_fixture.terms.ex.Pizza
    target = network_fixture.terms.ex.hasTopping
    paths = network_fixture._get_shortest_path(source, target, num_paths=2)
    assert len(paths) <= 2


def test_get_shortest_path_with_triples(network_fixture):
    source = network_fixture.terms.ex.Pizza
    target = network_fixture.terms.ex.hasTopping
    result = network_fixture.get_shortest_path(
        source, target, triples=True, num_paths=1
    )
    assert isinstance(result, list)
    assert isinstance(result[0], list)


def test_get_shortest_path_without_triples(network_fixture):
    source = network_fixture.terms.ex.Pizza
    target = network_fixture.terms.ex.hasTopping
    result = network_fixture.get_shortest_path(
        source, target, triples=False, num_paths=1
    )
    assert isinstance(result, list)


def test_get_shortest_path_stepped_query(network_fixture):
    source = network_fixture.terms.ex.Pizza
    target = network_fixture.terms.ex.Food
    parent = network_fixture.terms.ex.hasTopping
    target._parents.append(parent)
    result = network_fixture.get_shortest_path(source, target, triples=False)
    assert isinstance(result, list)
    target._parents = []


def test_get_shortest_path_stepped_multiple_paths_error(network_fixture):
    source = network_fixture.terms.ex.Pizza
    target = network_fixture.terms.ex.hasTopping
    parent = network_fixture.terms.ex.Food
    target._parents.append(parent)
    with pytest.raises(ValueError):
        network_fixture.get_shortest_path(source, target, num_paths=2)
    target._parents = []


def test_insert_namespaces(network_fixture):
    namespaces = {"ex": "http://example.org/ontology#"}
    result = network_fixture._insert_namespaces(namespaces)
    assert len(result) > 0
    assert "PREFIX ex:" in result[0]


def test_modify_destinations(network_fixture):
    dest1 = network_fixture.terms.ex.Pizza
    dest2 = network_fixture.terms.ex.Food
    destinations = [[dest1, dest2]]
    modified = network_fixture._modify_destinations(destinations)
    assert len(modified) == 1
    assert dest1 in modified[0]._parents


def test_is_already_in_destinations(network_fixture):
    obj_prop = network_fixture.terms.ex.hasTopping
    destinations = [obj_prop]
    assert network_fixture._is_already_in_destinations(obj_prop, destinations)


def test_is_not_in_destinations(network_fixture):
    obj_prop = network_fixture.terms.ex.hasTopping
    other_prop = network_fixture.terms.ex.hasPrice
    destinations = [obj_prop]
    assert not network_fixture._is_already_in_destinations(other_prop, destinations)


def test_create_query_single_source(network_fixture):
    source = network_fixture.terms.ex.Pizza
    query = network_fixture.create_query(source)
    assert isinstance(query, str)
    assert "SELECT DISTINCT" in query


def test_create_query_with_destination(network_fixture):
    source = network_fixture.terms.ex.Pizza
    dest = network_fixture.terms.ex.hasTopping
    query = network_fixture.create_query(source, dest)
    assert isinstance(query, str)
    assert "SELECT DISTINCT" in query


def test_create_query_multiple_destinations(network_fixture):
    source = network_fixture.terms.ex.Pizza
    dest1 = network_fixture.terms.ex.hasTopping
    dest2 = network_fixture.terms.ex.hasPrice
    query = network_fixture.create_query(source, [dest1, dest2], num_paths=1)
    assert isinstance(query, str)


def test_create_query_return_list(network_fixture):
    source = network_fixture.terms.ex.Pizza
    query = network_fixture.create_query(source, return_list=True)
    assert isinstance(query, list)


def test_create_query_data_property_source_error(network_fixture):
    source = network_fixture.terms.ex.hasPrice
    with pytest.raises(ValueError):
        network_fixture.create_query(source)


def test_create_query_multiple_destinations_multiple_paths_error(network_fixture):
    source = network_fixture.terms.ex.Pizza
    dest1 = network_fixture.terms.ex.hasTopping
    dest2 = network_fixture.terms.ex.hasPrice
    with pytest.raises(TypeError):
        network_fixture.create_query(source, [dest1, dest2], num_paths=2)


def test_prepare_destinations(network_fixture):
    source = network_fixture.terms.ex.Pizza
    dest = network_fixture.terms.ex.hasTopping
    destinations = [dest]
    result = network_fixture._prepare_destinations(destinations, source)
    assert len(result) > 0


def test_prepare_destinations_source_any_error(network_fixture):
    source = network_fixture.terms.ex.Pizza.any
    with pytest.raises(ValueError):
        network_fixture._prepare_destinations(None, source)


def test_prepare_destinations_multiple_conditions_error(network_fixture):
    source = network_fixture.terms.ex.Pizza
    dest1 = network_fixture.terms.ex.Pizza
    dest2 = network_fixture.terms.ex.Pizza
    dest1._condition = "condition1"
    dest2._condition = "condition2"
    with pytest.raises(ValueError):
        network_fixture._prepare_destinations([dest1, dest2], source)
    dest1._condition = None
    dest2._condition = None


def test_create_query_prefix(network_fixture):
    source = network_fixture.terms.ex.Pizza
    dest = network_fixture.terms.ex.hasTopping
    result = network_fixture._create_query_prefix(source, [dest])
    assert "SELECT DISTINCT" in result[0]
    assert "WHERE" in result[1]


def test_create_query_prefix_with_remote_source(network_fixture):
    source = network_fixture.terms.ex.Pizza
    dest = network_fixture.terms.ex.hasTopping
    result = network_fixture._create_query_prefix(
        source, [dest], remote_source="https://example.org/sparql"
    )
    assert "SERVICE" in result[2]


def test_create_query_prefix_invalid_remote_url(network_fixture):
    source = network_fixture.terms.ex.Pizza
    dest = network_fixture.terms.ex.hasTopping
    with pytest.raises(ValueError):
        network_fixture._create_query_prefix(source, [dest], remote_source="not-a-url")


def test_get_triples(network_fixture):
    source = network_fixture.terms.ex.Pizza
    dest = network_fixture.terms.ex.hasTopping
    queries, namespaces = network_fixture._get_triples(source, [dest], num_paths=1)
    assert len(queries) > 0
    assert len(namespaces) > 0


def test_add_types_for_source(network_fixture):
    source = network_fixture.terms.ex.Pizza
    query, namespaces = network_fixture._add_types_for_source(source)
    assert isinstance(query, list)
    assert isinstance(namespaces, list)


def test_add_types_for_destination(network_fixture):
    dest = network_fixture.terms.ex.Pizza.only
    query, namespaces = network_fixture._add_types_for_destination([dest])
    assert isinstance(query, list)
    assert isinstance(namespaces, list)


def test_add_filters_no_condition(network_fixture):
    dest = network_fixture.terms.ex.hasTopping
    result = network_fixture._add_filters([dest])
    assert "}" in result


def test_add_filters_with_condition(network_fixture):
    dest = network_fixture.terms.ex.Pizza
    dest._condition = "(?Pizza > 10)"
    result = network_fixture._add_filters([dest])
    assert "FILTER" in result[0]
    dest._condition = None


def test_add_limit_none(network_fixture):
    result = network_fixture._add_limit(None)
    assert result == []


def test_add_limit_with_value(network_fixture):
    result = network_fixture._add_limit(10)
    assert "LIMIT 10" in result[0]


def test_create_query_full(network_fixture):
    source = network_fixture.terms.ex.Pizza
    dest = network_fixture.terms.ex.hasTopping
    queries = network_fixture._create_query(source, [dest], num_paths=1)
    assert len(queries) > 0
    assert "SELECT DISTINCT" in queries[0]


def test_create_query_with_limit(network_fixture):
    source = network_fixture.terms.ex.Pizza
    dest = network_fixture.terms.ex.hasTopping
    queries = network_fixture._create_query(source, [dest], limit=10)
    assert "LIMIT 10" in queries[0]


def test_query_execution(network_fixture):
    kg = Graph()
    ex = Namespace("http://example.org/ontology#")
    kg.bind("ex", ex)
    kg.add((ex.MyPizza, RDF.type, ex.Pizza))
    kg.add((ex.MyPizza, ex.hasTopping, ex.Cheese))

    source = network_fixture.terms.ex.Pizza
    dest = network_fixture.terms.ex.hasTopping
    result = network_fixture.query(kg, source, [dest])
    assert result is not None


def test_query_execution_no_results(network_fixture):
    kg = Graph()
    source = network_fixture.terms.ex.Pizza
    dest = network_fixture.terms.ex.hasTopping
    result = network_fixture.query(kg, source, [dest])
    assert result is not None
    assert len(result) == 0


def test_query_execution_with_limit(network_fixture):
    kg = Graph()
    ex = Namespace("http://example.org/ontology#")
    kg.bind("ex", ex)
    kg.add((ex.MyPizza, RDF.type, ex.Pizza))
    kg.add((ex.MyPizza, ex.hasTopping, ex.Cheese))

    source = network_fixture.terms.ex.Pizza
    dest = network_fixture.terms.ex.hasTopping
    result = network_fixture.query(kg, source, [dest], limit=1)
    assert result is not None


def test_query_with_remote_endpoint(network_fixture):
    source = network_fixture.terms.ex.Pizza
    dest = network_fixture.terms.ex.hasTopping
    with pytest.raises(Exception):
        network_fixture.query("https://example.org/sparql", source, [dest])


def test_query_internal(network_fixture):
    kg = Graph()
    query_string = "SELECT DISTINCT ?s WHERE { ?s ?p ?o }"
    result = network_fixture._query(kg, query_string, return_df=True)
    assert result is not None
    assert len(result) == 0


def test_ontology_network_base_init(simple_onto):
    network = OntologyNetworkBase(simple_onto)
    assert network.onto == simple_onto
    assert network._terms is None
    assert network._g is None


def test_ontology_network_base_terms_lazy(simple_onto):
    network = OntologyNetworkBase(simple_onto)
    assert network._terms is None
    terms = network.terms
    assert network._terms is not None


def test_ontology_network_base_g_lazy(simple_onto):
    network = OntologyNetworkBase(simple_onto)
    assert network._g is None
    g = network.g
    assert network._g is not None


def test_ontology_network_base_add(simple_onto):
    network1 = OntologyNetworkBase(simple_onto)
    network2 = OntologyNetworkBase(simple_onto)
    combined = network1 + network2
    assert isinstance(combined, OntologyNetworkBase)


def test_ontology_network_base_radd(simple_onto):
    network1 = OntologyNetworkBase(simple_onto)
    network2 = OntologyNetworkBase(simple_onto)
    combined = network2.__radd__(network1)
    assert isinstance(combined, OntologyNetworkBase)


def test_ontology_network_base_attributes(simple_onto):
    network = OntologyNetworkBase(simple_onto)
    attrs = network.attributes
    assert attrs is not None


def test_ontology_network_base_namespaces(simple_onto):
    network = OntologyNetworkBase(simple_onto)
    ns = network.namespaces
    assert ns is not None


def test_ontology_network_base_extra_namespaces(simple_onto):
    network = OntologyNetworkBase(simple_onto)
    extra_ns = network.extra_namespaces
    assert extra_ns is not None


def test_ontology_network_base_add_namespace(simple_onto):
    network = OntologyNetworkBase(simple_onto)
    network.add_namespace("test", "http://test.org/")
    assert network._terms is None


def test_ontology_network_base_add_term(simple_onto):
    network = OntologyNetworkBase(simple_onto)
    network.add_term("http://example.org/ontology#NewClass", "class", namespace="ex")
    assert network._terms is None
    assert network._g is None


def test_ontology_network_base_add_path(simple_onto):
    network = OntologyNetworkBase(simple_onto)
    network.add_path(("ex:Pizza", "ex:hasTopping", "ex:Food"))
    assert network._terms is None
    assert network._g is None


def test_ontology_network_base_add_path_invalid_subject(simple_onto):
    network = OntologyNetworkBase(simple_onto)
    with pytest.raises(ValueError):
        network.add_path(("ex:Invalid", "ex:hasTopping", "ex:Food"))


def test_ontology_network_base_add_path_invalid_object(simple_onto):
    network = OntologyNetworkBase(simple_onto)
    with pytest.raises(ValueError):
        network.add_path(("ex:Pizza", "ex:hasTopping", "ex:Invalid"))


def test_ontology_network_init(tmp_path):
    owl_file = tmp_path / "test.owl"
    owl_content = """<?xml version="1.0"?>
    <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
             xmlns:owl="http://www.w3.org/2002/07/owl#"
             xmlns:ex="http://example.org/ontology#">
        <owl:Class rdf:about="http://example.org/ontology#Pizza"/>
    </rdf:RDF>
    """
    owl_file.write_text(owl_content)
    network = OntologyNetwork(str(owl_file), format="xml")
    assert network.onto is not None
