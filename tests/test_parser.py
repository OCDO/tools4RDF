import pytest
from rdflib import Graph, Namespace, RDF, RDFS, OWL, URIRef, Literal, BNode
from tools4rdf.network.parser import OntoParser, parse_ontology
from tools4rdf.network.term import OntoTerm


@pytest.fixture
def simple_graph():
    g = Graph()
    ex = Namespace("http://example.org/ontology#")
    g.bind("ex", ex)
    g.add((ex.Pizza, RDF.type, OWL.Class))
    g.add((ex.Food, RDF.type, OWL.Class))
    g.add((ex.Pizza, RDFS.subClassOf, ex.Food))
    return g


@pytest.fixture
def parser_with_properties():
    g = Graph()
    ex = Namespace("http://example.org/ontology#")
    g.bind("ex", ex)

    g.add((ex.Pizza, RDF.type, OWL.Class))
    g.add((ex.Person, RDF.type, OWL.Class))

    g.add((ex.hasTopping, RDF.type, OWL.ObjectProperty))
    g.add((ex.hasTopping, RDFS.domain, ex.Pizza))
    g.add((ex.hasTopping, RDFS.range, ex.Food))

    g.add((ex.hasPrice, RDF.type, OWL.DatatypeProperty))
    g.add((ex.hasPrice, RDFS.domain, ex.Pizza))

    return OntoParser(g)


@pytest.fixture
def parser_with_union():
    g = Graph()
    ex = Namespace("http://example.org/ontology#")
    g.bind("ex", ex)

    g.add((ex.Pizza, RDF.type, OWL.Class))
    g.add((ex.Pasta, RDF.type, OWL.Class))
    g.add((ex.Person, RDF.type, OWL.Class))

    union_node = BNode()
    g.add((union_node, RDF.type, OWL.Class))
    collection = BNode()
    g.add((union_node, OWL.unionOf, collection))
    g.add((collection, RDF.first, ex.Pizza))
    rest_node = BNode()
    g.add((collection, RDF.rest, rest_node))
    g.add((rest_node, RDF.first, ex.Pasta))
    g.add((rest_node, RDF.rest, RDF.nil))

    g.add((ex.hasFood, RDF.type, OWL.ObjectProperty))
    g.add((ex.hasFood, RDFS.domain, union_node))

    return OntoParser(g)


def test_parse_ontology_xml(tmp_path):
    owl_file = tmp_path / "test.owl"
    owl_content = """<?xml version="1.0"?>
    <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
             xmlns:owl="http://www.w3.org/2002/07/owl#"
             xmlns:ex="http://example.org/ontology#">
        <owl:Class rdf:about="http://example.org/ontology#Pizza"/>
    </rdf:RDF>
    """
    owl_file.write_text(owl_content)
    parser = parse_ontology(str(owl_file), format="xml")
    assert isinstance(parser, OntoParser)


def test_ontoparser_init():
    g = Graph()
    parser = OntoParser(g)
    assert parser.graph == g
    assert parser._data_dict is None


def test_ontoparser_lazy_initialization():
    g = Graph()
    parser = OntoParser(g)
    assert parser._data_dict is None
    classes = parser.classes
    assert parser._data_dict is not None


def test_ontoparser_add():
    g1 = Graph()
    ex = Namespace("http://example.org/ontology#")
    g1.add((ex.Pizza, RDF.type, OWL.Class))

    g2 = Graph()
    g2.add((ex.Pasta, RDF.type, OWL.Class))

    parser1 = OntoParser(g1)
    parser2 = OntoParser(g2)
    combined = parser1 + parser2

    assert isinstance(combined, OntoParser)
    assert (ex.Pizza, RDF.type, OWL.Class) in combined.graph
    assert (ex.Pasta, RDF.type, OWL.Class) in combined.graph


def test_ontoparser_radd():
    g1 = Graph()
    ex = Namespace("http://example.org/ontology#")
    g1.add((ex.Pizza, RDF.type, OWL.Class))

    g2 = Graph()
    g2.add((ex.Pasta, RDF.type, OWL.Class))

    parser1 = OntoParser(g1)
    parser2 = OntoParser(g2)
    combined = parser2.__radd__(parser1)

    assert isinstance(combined, OntoParser)


def test_base_iri():
    g = Graph()
    base = URIRef("http://example.org/ontology")
    g.add((base, RDF.type, OWL.Ontology))
    parser = OntoParser(g)
    assert parser.base_iri == "http://example.org/ontology"


def test_base_iri_none():
    g = Graph()
    parser = OntoParser(g)
    assert parser.base_iri is None


def test_extract_default_namespaces():
    g = Graph()
    ex = Namespace("http://example.org/ontology#")
    g.bind("ex", ex)
    parser = OntoParser(g)
    parser._extract_default_namespaces()
    assert "ex" in parser.namespaces
    assert parser.namespaces["ex"] == "http://example.org/ontology#"


def test_extract_classes(simple_graph):
    parser = OntoParser(simple_graph)
    parser._initialize()
    assert len(parser.classes) > 0
    assert OWL.Thing in parser.classes


def test_extract_object_properties():
    g = Graph()
    ex = Namespace("http://example.org/ontology#")
    g.bind("ex", ex)
    g.add((ex.hasTopping, RDF.type, OWL.ObjectProperty))
    g.add((ex.Pizza, RDF.type, OWL.Class))
    g.add((ex.hasTopping, RDFS.domain, ex.Pizza))

    parser = OntoParser(g)
    parser._initialize()

    assert "ex:hasTopping" in parser.attributes["object_property"]
    assert (
        parser.attributes["object_property"]["ex:hasTopping"].node_type
        == "object_property"
    )


def test_extract_data_properties():
    g = Graph()
    ex = Namespace("http://example.org/ontology#")
    g.bind("ex", ex)
    g.add((ex.hasPrice, RDF.type, OWL.DatatypeProperty))
    g.add((ex.Pizza, RDF.type, OWL.Class))
    g.add((ex.hasPrice, RDFS.domain, ex.Pizza))

    parser = OntoParser(g)
    parser._initialize()

    assert "ex:hasPrice" in parser.attributes["data_property"]
    assert (
        parser.attributes["data_property"]["ex:hasPrice"].node_type == "data_property"
    )
    assert "ex:hasPricevalue" in parser.attributes["data_nodes"]


def test_extract_subproperties():
    g = Graph()
    ex = Namespace("http://example.org/ontology#")
    g.bind("ex", ex)
    g.add((ex.hasTopping, RDF.type, OWL.ObjectProperty))
    g.add((ex.hasMozzarella, RDF.type, OWL.ObjectProperty))
    g.add((ex.hasMozzarella, RDFS.subPropertyOf, ex.hasTopping))

    parser = OntoParser(g)
    parser._initialize()

    assert (
        "ex:hasMozzarella"
        in parser.attributes["object_property"]["ex:hasTopping"].subclasses
    )


def test_create_term():
    g = Graph()
    ex = Namespace("http://example.org/ontology#")
    g.bind("ex", ex)
    g.add((ex.Pizza, RDF.type, OWL.Class))
    g.add((ex.Pizza, RDFS.comment, Literal("A delicious food")))

    parser = OntoParser(g)
    parser._extract_default_namespaces()
    term = parser.create_term(ex.Pizza)

    assert isinstance(term, OntoTerm)
    assert term.uri == "http://example.org/ontology#Pizza"
    assert term.description.toPython() == "A delicious food"


def test_get_description_with_comment():
    g = Graph()
    ex = Namespace("http://example.org/ontology#")
    g.add((ex.Pizza, RDFS.comment, Literal("Pizza comment")))

    parser = OntoParser(g)
    desc = parser.get_description(ex.Pizza)
    assert desc.toPython() == "Pizza comment"


def test_get_description_empty():
    g = Graph()
    ex = Namespace("http://example.org/ontology#")

    parser = OntoParser(g)
    desc = parser.get_description(ex.Pizza)
    assert desc == ""


def test_lookup_namespace():
    g = Graph()
    ex = Namespace("http://example.org/ontology#")
    g.bind("ex", ex)
    parser = OntoParser(g)
    parser._extract_default_namespaces()

    result = parser._lookup_namespace("http://example.org/ontology#Pizza")
    assert result == "ex"


def test_lookup_namespace_not_found():
    g = Graph()
    parser = OntoParser(g)
    result = parser._lookup_namespace("http://unknown.org/Pizza")
    assert result is None


def test_parse_subclasses():
    g = Graph()
    ex = Namespace("http://example.org/ontology#")
    g.bind("ex", ex)
    g.add((ex.Margherita, RDF.type, OWL.Class))
    g.add((ex.Pizza, RDF.type, OWL.Class))
    g.add((ex.Margherita, RDFS.subClassOf, ex.Pizza))

    parser = OntoParser(g)
    parser._initialize()

    assert "ex:Margherita" in parser.attributes["class"]["ex:Pizza"].subclasses


def test_add_subclasses_to_owlthing():
    g = Graph()
    ex = Namespace("http://example.org/ontology#")
    g.bind("ex", ex)
    g.add((ex.Pizza, RDF.type, OWL.Class))

    parser = OntoParser(g)
    parser._initialize()

    assert "ex:Pizza" in parser.attributes["class"]["owl:Thing"].subclasses


def test_parse_equivalents():
    g = Graph()
    ex = Namespace("http://example.org/ontology#")
    g.bind("ex", ex)
    g.add((ex.Pizza, RDF.type, OWL.Class))
    g.add((ex.Pie, RDF.type, OWL.Class))
    g.add((ex.Pizza, OWL.equivalentClass, ex.Pie))

    parser = OntoParser(g)
    parser._initialize()

    assert "ex:Pie" in parser.attributes["class"]["ex:Pizza"].equivalent_classes
    assert "ex:Pizza" in parser.attributes["class"]["ex:Pie"].equivalent_classes


def test_parse_named_individuals():
    g = Graph()
    ex = Namespace("http://example.org/ontology#")
    g.bind("ex", ex)
    g.add((ex.Pizza, RDF.type, OWL.Class))
    g.add((ex.MyPizza, RDF.type, OWL.NamedIndividual))
    g.add((ex.MyPizza, RDF.type, ex.Pizza))

    parser = OntoParser(g)
    parser._initialize()

    assert "ex:MyPizza" in parser.attributes["class"]["ex:Pizza"].named_individuals


def test_get_domain(parser_with_properties):
    domain = parser_with_properties.attributes["object_property"][
        "ex:hasTopping"
    ].domain
    assert "ex:Pizza" in domain


def test_get_range(parser_with_properties):
    rng = parser_with_properties.attributes["object_property"]["ex:hasTopping"].range
    assert "ex:Food" in rng


def test_unravel_relation():
    g = Graph()
    ex = Namespace("http://example.org/ontology#")

    collection = BNode()
    g.add((collection, RDF.first, ex.Pizza))
    rest_node = BNode()
    g.add((collection, RDF.rest, rest_node))
    g.add((rest_node, RDF.first, ex.Pasta))
    g.add((rest_node, RDF.rest, RDF.nil))

    parser = OntoParser(g)
    result = parser.unravel_relation(collection, [])

    assert len(result) == 2
    assert ex.Pizza in result
    assert ex.Pasta in result


def test_lookup_node_simple():
    g = Graph()
    ex = Namespace("http://example.org/ontology#")
    g.bind("ex", ex)
    g.add((ex.Pizza, RDF.type, OWL.Class))

    parser = OntoParser(g)
    parser._extract_default_namespaces()
    parser.extract_classes()
    parser.add_classes_to_attributes()

    result = parser.lookup_node(ex.Pizza)
    assert "ex:Pizza" in result


def test_lookup_node_blank():
    g = Graph()
    ex = Namespace("http://example.org/ontology#")
    g.bind("ex", ex)

    union_node = BNode()
    g.add((union_node, RDF.type, OWL.Class))
    collection = BNode()
    g.add((union_node, OWL.unionOf, collection))
    g.add((collection, RDF.first, ex.Pizza))
    g.add((collection, RDF.rest, RDF.nil))

    parser = OntoParser(g)
    parser._extract_default_namespaces()
    parser.extract_classes()

    node_str = union_node.toPython()
    assert node_str in parser.mappings


def test_lookup_class():
    g = Graph()
    ex = Namespace("http://example.org/ontology#")
    g.bind("ex", ex)
    g.add((ex.Pizza, RDF.type, OWL.Class))

    parser = OntoParser(g)
    parser._initialize()

    result = parser.lookup_class(ex.Pizza)
    assert "ex:Pizza" in result


def test_lookup_class_blank_node():
    g = Graph()
    ex = Namespace("http://example.org/ontology#")
    g.bind("ex", ex)
    g.add((ex.Pizza, RDF.type, OWL.Class))

    union_node = BNode()

    parser = OntoParser(g)
    parser._initialize()

    result = parser.lookup_class(union_node)
    assert isinstance(result, list)


def test_get_attributes():
    g = Graph()
    ex = Namespace("http://example.org/ontology#")
    g.bind("ex", ex)
    g.add((ex.Pizza, RDF.type, OWL.Class))
    g.add((ex.hasTopping, RDF.type, OWL.ObjectProperty))

    parser = OntoParser(g)
    parser._initialize()

    attrs = parser.get_attributes()
    assert "ex" in attrs
    assert "Pizza" in attrs["ex"]


def test_get_networkx_graph():
    g = Graph()
    ex = Namespace("http://example.org/ontology#")
    g.bind("ex", ex)
    g.add((ex.Pizza, RDF.type, OWL.Class))
    g.add((ex.hasTopping, RDF.type, OWL.ObjectProperty))
    g.add((ex.hasTopping, RDFS.domain, ex.Pizza))

    parser = OntoParser(g)
    parser._initialize()

    nx_graph = parser.get_networkx_graph()
    assert "ex:Pizza" in nx_graph.nodes()
    assert "ex:hasTopping" in nx_graph.nodes()


def test_add_term_class():
    g = Graph()
    ex = Namespace("http://example.org/ontology#")
    g.bind("ex", ex)

    parser = OntoParser(g)
    parser.add_term("http://example.org/ontology#NewPizza", "class", namespace="ex")

    assert (
        URIRef("http://example.org/ontology#NewPizza"),
        RDF.type,
        OWL.Class,
    ) in parser.graph


def test_add_term_object_property():
    g = Graph()
    ex = Namespace("http://example.org/ontology#")
    g.bind("ex", ex)

    parser = OntoParser(g)
    parser.add_term(
        "http://example.org/ontology#newProperty", "object_property", namespace="ex"
    )

    assert (
        URIRef("http://example.org/ontology#newProperty"),
        RDF.type,
        OWL.ObjectProperty,
    ) in parser.graph


def test_add_term_data_property():
    g = Graph()
    ex = Namespace("http://example.org/ontology#")
    g.bind("ex", ex)

    parser = OntoParser(g)
    parser.add_term(
        "http://example.org/ontology#newDataProp", "data_property", namespace="ex"
    )

    assert (
        URIRef("http://example.org/ontology#newDataProp"),
        RDF.type,
        OWL.DatatypeProperty,
    ) in parser.graph


def test_add_term_invalid_type():
    g = Graph()
    parser = OntoParser(g)

    with pytest.raises(ValueError):
        parser.add_term("http://example.org/ontology#Invalid", "invalid_type")


def test_add_term_with_domain_range():
    g = Graph()
    ex = Namespace("http://example.org/ontology#")
    g.bind("ex", ex)

    parser = OntoParser(g)
    parser.add_term(
        "http://example.org/ontology#hasProperty",
        "object_property",
        namespace="ex",
        dm=["http://example.org/ontology#Pizza"],
        rn=["http://example.org/ontology#Topping"],
    )

    assert (
        URIRef("http://example.org/ontology#hasProperty"),
        RDFS.domain,
        URIRef("http://example.org/ontology#Pizza"),
    ) in parser.graph
    assert (
        URIRef("http://example.org/ontology#hasProperty"),
        RDFS.range,
        URIRef("http://example.org/ontology#Topping"),
    ) in parser.graph


def test_add_namespace():
    g = Graph()
    parser = OntoParser(g)
    parser._initialize()

    parser.add_namespace("custom", "http://custom.org/")

    assert parser._data_dict is None


def test_extract_values():
    g = Graph()
    ex = Namespace("http://example.org/ontology#")
    g.add((ex.Pizza, RDFS.comment, Literal("comment")))

    parser = OntoParser(g)
    result = parser.extract_values(ex.Pizza, RDFS.comment)

    assert result == Literal("comment")


def test_extract_values_none():
    g = Graph()
    ex = Namespace("http://example.org/ontology#")

    parser = OntoParser(g)
    result = parser.extract_values(ex.Pizza, RDFS.comment)

    assert result is None


def test_union_class_extraction():
    g = Graph()
    ex = Namespace("http://example.org/ontology#")
    g.bind("ex", ex)

    g.add((ex.Pizza, RDF.type, OWL.Class))
    g.add((ex.Pasta, RDF.type, OWL.Class))

    union_node = BNode()
    g.add((union_node, RDF.type, OWL.Class))
    collection = BNode()
    g.add((union_node, OWL.unionOf, collection))
    g.add((collection, RDF.first, ex.Pizza))
    rest_node = BNode()
    g.add((collection, RDF.rest, rest_node))
    g.add((rest_node, RDF.first, ex.Pasta))
    g.add((rest_node, RDF.rest, RDF.nil))

    parser = OntoParser(g)
    parser._initialize()

    union_key = union_node.toPython()
    assert union_key in parser.mappings
    assert parser.mappings[union_key]["type"] == "union"
    assert "ex:Pizza" in parser.mappings[union_key]["items"]
    assert "ex:Pasta" in parser.mappings[union_key]["items"]


def test_intersection_class_extraction():
    g = Graph()
    ex = Namespace("http://example.org/ontology#")
    g.bind("ex", ex)

    g.add((ex.Pizza, RDF.type, OWL.Class))
    g.add((ex.Italian, RDF.type, OWL.Class))

    intersection_node = BNode()
    g.add((intersection_node, RDF.type, OWL.Class))
    collection = BNode()
    g.add((intersection_node, OWL.intersectionOf, collection))
    g.add((collection, RDF.first, ex.Pizza))
    rest_node = BNode()
    g.add((collection, RDF.rest, rest_node))
    g.add((rest_node, RDF.first, ex.Italian))
    g.add((rest_node, RDF.rest, RDF.nil))

    parser = OntoParser(g)
    parser._initialize()

    intersection_key = intersection_node.toPython()
    assert intersection_key in parser.mappings
    assert parser.mappings[intersection_key]["type"] == "intersection"


def test_domain_with_union(parser_with_union):
    domain = parser_with_union.attributes["object_property"]["ex:hasFood"].domain
    assert "ex:Pizza" in domain
    assert "ex:Pasta" in domain


def test_recursively_add_subclasses():
    g = Graph()
    ex = Namespace("http://example.org/ontology#")
    g.bind("ex", ex)

    g.add((ex.Food, RDF.type, OWL.Class))
    g.add((ex.Pizza, RDF.type, OWL.Class))
    g.add((ex.Margherita, RDF.type, OWL.Class))

    g.add((ex.Pizza, RDFS.subClassOf, ex.Food))
    g.add((ex.Margherita, RDFS.subClassOf, ex.Pizza))

    parser = OntoParser(g)
    parser._initialize()

    assert "ex:Margherita" in parser.attributes["class"]["ex:Food"].subclasses


def test_recursively_add_equivalents():
    g = Graph()
    ex = Namespace("http://example.org/ontology#")
    g.bind("ex", ex)

    g.add((ex.Pizza, RDF.type, OWL.Class))
    g.add((ex.Pie, RDF.type, OWL.Class))
    g.add((ex.FlatBread, RDF.type, OWL.Class))

    g.add((ex.Pizza, OWL.equivalentClass, ex.Pie))
    g.add((ex.Pie, OWL.equivalentClass, ex.FlatBread))

    parser = OntoParser(g)
    parser._initialize()

    assert "ex:FlatBread" in parser.attributes["class"]["ex:Pizza"].equivalent_classes


def test_recheck_namespaces():
    g = Graph()
    ex = Namespace("http://example.org/ontology#")
    g.bind("ex", ex)
    g.add((ex.Pizza, RDF.type, OWL.Class))

    parser = OntoParser(g)
    parser._initialize()

    assert "ex" in parser.namespaces
