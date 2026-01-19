import pytest
from tools4rdf.network.term import (
    OntoTerm,
    is_url,
    _get_namespace_and_name,
    _get_namespace_with_prefix,
    strip_name,
)


def test_is_url_valid():
    assert is_url("https://example.org/ontology")
    assert is_url("http://example.org")
    assert is_url("ftp://files.example.com/data")


def test_is_url_invalid():
    assert not is_url("not a url")
    assert not is_url("example.org")
    assert not is_url("/local/path")


def test_get_namespace_and_name_with_hash():
    uri = "http://example.org/ontology#Pizza"
    namespace, name = _get_namespace_and_name(uri)
    assert namespace == "ontology"
    assert name == "Pizza"


def test_get_namespace_and_name_with_slash():
    uri = "http://example.org/ontology/Pizza"
    namespace, name = _get_namespace_and_name(uri)
    assert namespace == "ontology"
    assert name == "Pizza"


def test_get_namespace_and_name_simple():
    uri = "Pizza"
    namespace, name = _get_namespace_and_name(uri)
    assert namespace == ""
    assert name == "Pizza"


def test_get_namespace_with_prefix_hash():
    uri = "http://example.org/ontology#Pizza"
    result = _get_namespace_with_prefix(uri)
    assert result == "http://example.org/ontology"


def test_get_namespace_with_prefix_slash():
    uri = "http://example.org/ontology/Pizza"
    result = _get_namespace_with_prefix(uri)
    assert result == "http://example.org/ontology/"


def test_strip_name_returns_name():
    uri = "http://example.org/ontology#Pizza"
    result = strip_name(uri, get_what="name")
    assert result == "ontology:Pizza"


def test_strip_name_returns_namespace():
    uri = "http://example.org/ontology#Pizza"
    result = strip_name(uri, get_what="namespace")
    assert result == "ontology"


def test_strip_name_with_provided_namespace():
    uri = "http://example.org/ontology#Pizza"
    result = strip_name(uri, get_what="name", namespace="custom")
    assert result == "custom:Pizza"


def test_strip_name_invalid_option():
    uri = "http://example.org/ontology#Pizza"
    with pytest.raises(ValueError):
        strip_name(uri, get_what="invalid")


def test_ontoterm_init_with_uri():
    term = OntoTerm(uri="http://example.org/ontology#Pizza")
    assert term.uri == "http://example.org/ontology#Pizza"
    assert term.namespace == "ontology"


def test_ontoterm_init_with_name():
    term = OntoTerm(name="pizza:Pizza", uri="http://example.org#Pizza")
    assert term.name == "pizza:Pizza"


def test_ontoterm_init_without_uri_and_name():
    with pytest.raises(ValueError):
        OntoTerm()


def test_ontoterm_uri_property():
    term = OntoTerm(uri="http://example.org#Pizza")
    assert term.uri == "http://example.org#Pizza"
    term.uri = "http://new.org#Food"
    assert term.uri == "http://new.org#Food"


def test_ontoterm_description_single_string():
    term = OntoTerm(uri="http://example.org#Pizza", description="A pizza")
    assert term.description == "A pizza"


def test_ontoterm_description_list():
    term = OntoTerm(uri="http://example.org#Pizza", description=["First", "Second"])
    assert term.description == "First. Second"


def test_ontoterm_description_empty_list():
    term = OntoTerm(uri="http://example.org#Pizza", description=[])
    assert term.description == ""


def test_ontoterm_name_without_prefix():
    term = OntoTerm(uri="http://example.org#Pizza", name="pizza:Margherita-Special")
    assert term.name_without_prefix == "MargheritaSpecial"


def test_ontoterm_query_name_data_property():
    term = OntoTerm(
        uri="http://example.org#hasPrice",
        name="pizza:hasPrice",
        node_type="data_property",
    )
    assert term.query_name == "pizza:hasPricevalue"


def test_ontoterm_query_name_other_type():
    term = OntoTerm(
        uri="http://example.org#Pizza", name="pizza:Pizza", node_type="class"
    )
    assert term.query_name == "pizza:Pizza"


def test_ontoterm_variable_name_no_parents():
    term = OntoTerm(uri="http://example.org#Pizza", name="pizza:Pizza")
    assert term.variable_name == "Pizza"


def test_ontoterm_variable_name_with_parents():
    parent = OntoTerm(uri="http://example.org#Food", name="pizza:Food")
    term = OntoTerm(uri="http://example.org#Pizza", name="pizza:Pizza")
    term._parents.append(parent)
    assert term.variable_name == "Food_Pizza"


def test_ontoterm_variable_name_data_property():
    term = OntoTerm(
        uri="http://example.org#hasPrice",
        name="pizza:hasPrice",
        node_type="data_property",
    )
    assert term.variable_name == "hasPricevalue"


def test_ontoterm_any_property():
    term = OntoTerm(uri="http://example.org#Pizza", name="pizza:Pizza")
    any_term = term.any
    assert any_term._enforce_type is False
    assert any_term._add_subclass is False


def test_ontoterm_all_subtypes_property():
    term = OntoTerm(uri="http://example.org#Pizza", name="pizza:Pizza")
    all_term = term.all_subtypes
    assert all_term._enforce_type is False
    assert all_term._add_subclass is True


def test_ontoterm_only_property():
    term = OntoTerm(uri="http://example.org#Pizza", name="pizza:Pizza")
    only_term = term.only
    assert only_term._enforce_type is True
    assert only_term._add_subclass is False


def test_ontoterm_repr():
    term = OntoTerm(uri="http://example.org#Pizza", name="pizza:Pizza")
    assert str(term) == "pizza:Pizza"


def test_ontoterm_clean_datatype():
    term = OntoTerm(uri="http://example.org#Pizza")
    assert term._clean_datatype("str") == "string"
    assert term._clean_datatype("int") == "int"


def test_ontoterm_eq_operator_data_property():
    term = OntoTerm(
        uri="http://example.org#hasPrice",
        name="pizza:hasPrice",
        node_type="data_property",
        rn=["float"],
    )
    result = term == 10.5
    assert result._condition == '(?hasPricevalue="10.5"^^xsd:float)'


def test_ontoterm_eq_operator_non_data_property():
    term1 = OntoTerm(
        uri="http://example.org#Pizza", name="pizza:Pizza", node_type="class"
    )
    term2 = OntoTerm(
        uri="http://example.org#Pizza", name="pizza:Pizza", node_type="class"
    )
    assert (term1 == term2) is True


def test_ontoterm_lt_operator():
    term = OntoTerm(
        uri="http://example.org#hasPrice",
        name="pizza:hasPrice",
        node_type="data_property",
        rn=["float"],
    )
    result = term < 10.5
    assert result._condition == '(?hasPricevalue<"10.5"^^xsd:float)'


def test_ontoterm_le_operator():
    term = OntoTerm(
        uri="http://example.org#hasPrice",
        name="pizza:hasPrice",
        node_type="data_property",
        rn=["float"],
    )
    result = term <= 10.5
    assert result._condition == '(?hasPricevalue<="10.5"^^xsd:float)'


def test_ontoterm_gt_operator():
    term = OntoTerm(
        uri="http://example.org#hasPrice",
        name="pizza:hasPrice",
        node_type="data_property",
        rn=["float"],
    )
    result = term > 10.5
    assert result._condition == '(?hasPricevalue>"10.5"^^xsd:float)'


def test_ontoterm_ge_operator():
    term = OntoTerm(
        uri="http://example.org#hasPrice",
        name="pizza:hasPrice",
        node_type="data_property",
        rn=["float"],
    )
    result = term >= 10.5
    assert result._condition == '(?hasPricevalue>="10.5"^^xsd:float)'


def test_ontoterm_ne_operator():
    term = OntoTerm(
        uri="http://example.org#hasPrice",
        name="pizza:hasPrice",
        node_type="data_property",
        rn=["float"],
    )
    result = term != 10.5
    assert result._condition == '(?hasPricevalue!="10.5"^^xsd:float)'


def test_ontoterm_and_operator():
    term1 = OntoTerm(
        uri="http://example.org#hasPrice",
        name="pizza:hasPrice",
        node_type="data_property",
        rn=["float"],
    )
    term2 = OntoTerm(
        uri="http://example.org#hasWeight",
        name="pizza:hasWeight",
        node_type="data_property",
        rn=["float"],
    )
    cond1 = term1 > 10
    cond2 = term2 < 5
    result = cond1 & cond2
    assert "&&" in result._condition
    assert "hasPricevalue" in result._condition
    assert "hasWeightvalue" in result._condition


def test_ontoterm_or_operator():
    term1 = OntoTerm(
        uri="http://example.org#hasPrice",
        name="pizza:hasPrice",
        node_type="data_property",
        rn=["float"],
    )
    term2 = OntoTerm(
        uri="http://example.org#hasWeight",
        name="pizza:hasWeight",
        node_type="data_property",
        rn=["float"],
    )
    cond1 = term1 > 10
    cond2 = term2 < 5
    result = cond1 | cond2
    assert "||" in result._condition
    assert "hasPricevalue" in result._condition
    assert "hasWeightvalue" in result._condition


def test_ontoterm_matmul_operator_deprecated():
    term1 = OntoTerm(uri="http://example.org#Pizza", name="pizza:Pizza")
    term2 = OntoTerm(uri="http://example.org#Food", name="pizza:Food")
    with pytest.warns(UserWarning):
        result = term1 @ term2
    assert len(result._parents) == 1


def test_ontoterm_refresh_condition():
    term = OntoTerm(
        uri="http://example.org#hasPrice",
        name="pizza:hasPrice",
        node_type="data_property",
        rn=["float"],
    )
    cond = term > 10
    cond.refresh_condition()
    assert cond._condition is None
    assert cond._condition_parents == []


def test_ontoterm_refresh():
    term = OntoTerm(uri="http://example.org#Pizza", name="pizza:Pizza")
    parent = OntoTerm(uri="http://example.org#Food", name="pizza:Food")
    term._parents.append(parent)
    term._condition = "test"
    term.refresh()
    assert term._condition is None
    assert term._parents == []
    assert term._condition_parents == []


def test_ontoterm_operator_type_checking():
    term = OntoTerm(
        uri="http://example.org#Pizza", name="pizza:Pizza", node_type="class"
    )
    with pytest.raises(TypeError):
        term < 10


def test_ontoterm_operator_requires_data_property():
    term = OntoTerm(
        uri="http://example.org#Pizza", name="pizza:Pizza", node_type="class"
    )
    with pytest.raises(TypeError):
        term > 5


def test_ontoterm_and_requires_condition():
    term1 = OntoTerm(
        uri="http://example.org#hasPrice",
        name="pizza:hasPrice",
        node_type="data_property",
        rn=["float"],
    )
    term2 = OntoTerm(
        uri="http://example.org#hasWeight",
        name="pizza:hasWeight",
        node_type="data_property",
        rn=["float"],
    )
    with pytest.raises(ValueError):
        term1 & term2


def test_ontoterm_and_requires_ontoterm():
    term = OntoTerm(
        uri="http://example.org#hasPrice",
        name="pizza:hasPrice",
        node_type="data_property",
        rn=["float"],
    )
    cond = term > 10
    with pytest.raises(TypeError):
        cond & "not a term"
