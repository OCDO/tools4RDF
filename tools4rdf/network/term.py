"""
This module provides utilities for working with ontology terms, specifically for RDF (Resource Description Framework) data. 
It includes helper functions for parsing and manipulating URIs, as well as a class `OntoTerm` for representing and managing 
ontology terms with various properties and behaviors.

The `OntoTerm` class encapsulates the details of an ontology term, including its URI, namespace, type, domain, range, 
data type, and other metadata. It also provides methods for generating SPARQL query names, handling conditions, and 
overloading operators for logical and comparison operations.

Key Features:
- Parsing URIs to extract namespaces and names.
- Managing ontology term properties such as description, label, and name.
- Support for SPARQL query generation with namespace and prefix handling.
- Operator overloading for logical (`and`, `or`) and comparison (`<`, `>`, `==`, etc.) operations.
- Utilities for handling data properties, object properties, and class hierarchies.

This module is designed to facilitate the creation and manipulation of ontology terms in RDF-based systems, 
making it easier to work with semantic data and SPARQL queries.
"""

from rdflib import URIRef
import numbers
import copy
import warnings


def _get_namespace_and_name(uri):
    """
    Extracts the namespace and name from a given URI.

    Parameters
    ----------
    uri : str
        The URI string to be parsed.

    Returns
    -------
    tuple
        A tuple containing:
        - namespace (str): The namespace extracted from the URI. If no namespace is found, an empty string is returned.
        - name (str): The name extracted from the URI.
    """
    uri_split = uri.split("#")
    if len(uri_split) > 1:
        # possible that delimiter is #
        name = uri_split[-1]
        namespace_split = uri_split[0].split("/")
        namespace = namespace_split[-1]
    else:
        uri_split = uri.split("/")
        if len(uri_split) > 1:
            name = uri_split[-1]
            namespace = uri_split[-2]
        else:
            name = uri_split[-1]
            namespace = ""
    return namespace, name


def _get_namespace_with_prefix(uri):
    """
    Extracts the namespace from a given URI, appending a trailing delimiter if necessary.

    Parameters
    ----------
    uri : str
        The URI from which the namespace is to be extracted.

    Returns
    -------
    str
        The extracted namespace. If the URI does not contain a recognizable delimiter
        ('#' or '/'), an empty string is returned.
    """
    uri_split = uri.split("#")
    if len(uri_split) > 1:
        # possible that delimiter is #
        namespace = uri_split[0]
    else:
        uri_split = uri.split("/")
        if len(uri_split) > 1:
            namespace = "/".join(uri_split[:-1])
            if namespace[-1] != "#":
                namespace += "/"
        else:
            namespace = ""
    return namespace


def strip_name(uri, get_what="name", namespace=None):
    """
    Extracts and returns either the namespace or the full name (namespace:name) 
    from a given URI.

    Parameters
    ----------
    uri : str
        The URI from which the namespace and name are to be extracted.
    get_what : str, optional
        Specifies what to return: "namespace" to return only the namespace, 
        or "name" to return the full name in the format "namespace:name". 
        Default is "name".
    namespace : str, optional
        If provided, this value will be used as the namespace instead of 
        extracting it from the URI. Default is None.

    Returns
    -------
    str
        The extracted namespace or the full name (namespace:name), depending 
        on the value of `get_what`.
    """
    if namespace is None:
        namespace, name = _get_namespace_and_name(uri)
    else:
        _, name = _get_namespace_and_name(uri)
    if get_what == "namespace":
        return namespace
    elif get_what == "name":
        return ":".join([namespace, name])
    else:
        raise ValueError("get_what must be either namespace or name")


class OntoTerm:
    def __init__(
        self,
        uri=None,
        namespace=None,
        node_type=None,
        dm=[],
        rn=[],
        data_type=None,
        node_id=None,
        delimiter="/",
        description=None,
        label=None,
        target=None,
        name=None,
    ):

        if uri is None and name is None:
            raise ValueError("Either uri or name must be provided!")
        self.uri = uri
        # type: can be object property, data property, or class
        self.node_type = node_type
        # now we need domain and range
        self.domain = dm
        self.range = rn
        # datatype, that is only need for data properties
        self.data_type = data_type
        # identifier
        self.node_id = node_id
        self.associated_data_node = None
        self.subclasses = []
        self.named_individuals = []
        self.equivalent_classes = []
        self.subproperties = []
        self.delimiter = delimiter
        self._description = None
        self.description = description
        self.label = label
        self._label = None
        self.is_domain_of = []
        self.is_range_of = []
        self._condition = None
        if uri is not None and namespace is None:
            namespace = strip_name(uri, get_what="namespace")
        self.namespace = namespace
        # name of the class
        self._name = None
        self.name = name
        # parents for the class; these are accumulated
        # when using the >> operator
        self._parents = []
        # condition parents are the parents that have conditions
        # these are accumulated when using the & or || operators
        self._condition_parents = []
        self.target = target
        self._enforce_type = True
        self._add_subclass = False

    @property
    def URIRef(self):
        return URIRef(self._uri)

    @property
    def uri(self):
        """
        Get the URI of the ontology term.

        Returns
        -------
        str
            The URI of the ontology term.
        """
        return self._uri

    @uri.setter
    def uri(self, val):
        self._uri = val

    @property
    def description(self):
        """
        Get the description of the term.

        Returns
        -------
        str
            The description of the term.
        """
        return self._description

    @description.setter
    def description(self, val):
        if isinstance(val, list):
            if len(val) == 0:
                val = ""
            elif len(val) > 1:
                val = ". ".join(val)
            else:
                val = val[0]
        self._description = val

    @property
    def label(self):
        """
        Get the label of the term.

        Returns
        -------
        str
            The label of the term.
        """
        return self._label

    @label.setter
    def label(self, val):
        if isinstance(val, list):
            if len(val) == 0:
                val = ""
            elif len(val) > 1:
                val = ". ".join(val)
            else:
                val = val[0]
        self._label = val

    @property
    def name(self):
        """
        Get the name of the term.

        Returns
        -------
        str
            The name of the term.
        """
        return self._name

    @name.setter
    def name(self, val):
        if val is None:
            val = strip_name(
                self.uri,
                get_what="name",
                namespace=self.namespace,
            )
        self._name = val

    @property
    def name_without_prefix(self):
        """
        Get the name without the namespace prefix.

        Returns
        -------
        str
            The name of the term without the namespace prefix.
        """
        name = self.name
        name = name.replace("–", "")
        name = name.replace("-", "")
        name = name.split(":")[-1]
        return name

    @property
    def namespace_with_prefix(self):
        """
        Get the namespace of the term with the prefix.

        Returns
        -------
        str
            The namespace of the term with the prefix.
        """
        return _get_namespace_with_prefix(self.uri)

    @property
    def namespace_object(self):
        """
        Get the namespace object for the term.

        Returns
        -------
        object
            The namespace object for the term.

        """
        return self.URIRef

    @property
    def query_name(self):
        """
        Get the name of the term as it appears in a SPARQL query.

        Returns
        -------
        str
            The name of the term in a SPARQL query.

        Notes
        -----
        If the term is a data property, the name will be appended with "value".

        """
        if self.node_type == "data_property":
            return self.name + "value"
        # elif self.node_type == "object_property":
        #    if len(self.range) > 0:
        #        # this has a domain
        #        return self.range[0]
        return self.name

    @property
    def variable_name(self):
        """
        Get the name of the term to use as a variable in a SPARQL query.

        Returns
        -------
        str
            The name of the term in a SPARQL query.

        """
        name_list = [x.name_without_prefix for x in self._parents]
        name_list.append(self.name_without_prefix)
        name = "_".join(name_list)

        if self.node_type == "data_property":
            return name + "value"

        return name

    @property
    def query_name_without_prefix(self):
        """
        Get the name of the term as it appears in a SPARQL query without prefix.

        Returns
        -------
        str
            The name of the term in a SPARQL query.

        Notes
        -----
        If the term is a data property, the name will be suffixed with "value".
        """
        if self.node_type == "data_property":
            return self.name_without_prefix + "value"
        return self.name_without_prefix

    @property
    def any(self):
        # this indicates that type enforcing is not needed
        item = copy.deepcopy(self)
        item._enforce_type = False
        return item

    @property
    def all_subtypes(self):
        # this indicates that type enforcing is not needed
        item = copy.deepcopy(self)
        item._add_subclass = True
        return item

    def toPython(self):
        return self.uri

    def __repr__(self):
        # if self.description is not None:
        #    return str(self.name + "\n" + self.description)
        # else:
        return str(self.name)

    def _clean_datatype(self, r):
        if r == "str":
            return "string"
        return r

    # convenience methods for overload checking
    def _ensure_condition_exists(self):
        if self._condition is None:
            raise ValueError(
                "Individual terms should have condition for this operation!"
            )

    def _is_term(self, val):
        if not isinstance(val, OntoTerm):
            raise TypeError("can only be performed with an OntoTerm!")

    def _is_number(self, val):
        if not isinstance(val, numbers.Number):
            raise TypeError("can only be performed with a number!")

    def _is_data_node(self):
        if not self.node_type == "data_property":
            raise TypeError(
                "This operation can only be performed with a data property!"
            )

    def _create_condition_string(self, condition, val):
        return f'(?{self.variable_name}{condition}"{val}"^^xsd:{self._clean_datatype(self.range[0])})'

    # overloading operators
    def __eq__(self, val):
        """
        =
        """
        # print("eq")
        # print(f'lhs {self} rhs {val}')
        if self.node_type == "data_property":
            item = copy.deepcopy(self)
            item._condition = item._create_condition_string("=", val)
            return item
        else:
            return self.name == val.name

    def __lt__(self, val):
        self._is_number(val)
        self._is_data_node()
        item = copy.deepcopy(self)
        item._condition = item._create_condition_string("<", val)
        return item

    def __le__(self, val):
        self._is_number(val)
        self._is_data_node()
        item = copy.deepcopy(self)
        item._condition = item._create_condition_string("<=", val)
        return item

    def __ne__(self, val):
        # self._is_number(val)
        self._is_data_node()
        item = copy.deepcopy(self)
        item._condition = item._create_condition_string("!=", val)
        return item

    def __ge__(self, val):
        self._is_number(val)
        self._is_data_node()
        item = copy.deepcopy(self)
        item._condition = item._create_condition_string(">=", val)
        return item

    def __gt__(self, val):
        # print("gt")
        # print(f'lhs {self} rhs {val}')
        self._is_number(val)
        self._is_data_node()
        self._condition = self._create_condition_string(">", val)
        return self

    def __and__(self, term):
        self._is_term(term)
        self._is_data_node()
        term._is_data_node()
        self._ensure_condition_exists()
        term._ensure_condition_exists()
        item = copy.deepcopy(self)
        item._condition = "&&".join([item._condition, term._condition])
        item._condition = f"({item._condition})"
        item._condition_parents.append(copy.deepcopy(term))
        # and clean up the inbound term
        if item.name != term.name:
            term.refresh_condition()
        return item

    def and_(self, term):
        self.__and__(term)

    def __or__(self, term):
        self._is_term(term)
        self._is_data_node()
        term._is_data_node()
        self._ensure_condition_exists()
        term._ensure_condition_exists()
        item = copy.deepcopy(self)
        item._condition = "||".join([item._condition, term._condition])
        item._condition = f"({item._condition})"
        item._condition_parents.append(copy.deepcopy(term))
        # and clean up the inbound term
        if item.name != term.name:
            term.refresh_condition()
        return item

    def or_(self, term):
        self.__or__(term)

    def __matmul__(self, term):
        # we will phase out this operator soon
        warnings.warn(
            "The @ operator is deprecated and will be removed in future versions. termA@termB should be [termA, termB] instead.",
        )
        item = copy.deepcopy(self)
        item._parents.append(copy.deepcopy(term))
        return item

    def refresh_condition(self):
        self._condition = None
        self._condition_parents = []

    def refresh(self):
        self._condition = None
        self._parents = []
        self._condition_parents = []
