"""
This module provides functionality for parsing and manipulating RDF/OWL ontologies. 
It defines the `OntoParser` class, which is used to extract and process ontology 
data, including classes, properties, namespaces, and relationships. The module 
leverages the `rdflib` library for RDF graph operations and `networkx` for graph 
representations.

Key Features:
- Parse RDF/OWL ontology files and extract structured data.
- Manage ontology classes, object properties, and data properties.
- Handle namespaces and mappings within the ontology.
- Support for subclass and equivalent class relationships.
- Generate a NetworkX graph representation of the ontology.
- Add new terms and namespaces to the ontology dynamically.

Dependencies:
- `rdflib` for RDF graph parsing and manipulation.
- `networkx` for graph-based representations of ontology structures.

Usage:
This module is designed to be used as part of a larger ontology processing pipeline. 
The `OntoParser` class provides methods for extracting and analyzing ontology data, 
as well as for extending the ontology with new terms and namespaces.
"""

import os
import networkx as nx

from tools4rdf.network.term import OntoTerm, strip_name
from tools4rdf.network.patch import patch_terms
from rdflib import Graph, RDF, RDFS, OWL, BNode, URIRef


def parse_ontology(infile, format="xml"):
    """
    Parses an ontology file and returns an OntoParser object.

    Parameters
    ----------
    infile : str
        The path to the ontology file to be parsed.
    format : str, optional
        The format of the ontology file (default is "xml").

    Returns
    -------
    OntoParser
        An instance of OntoParser initialized with the parsed ontology graph.
    """
    graph = Graph()
    graph.parse(infile, format=format)
    return OntoParser(graph)


class OntoParser:
    """
    A parser for extracting and managing ontology data from RDF graphs.

    This class provides methods to parse RDF graphs and extract ontology-related
    information such as classes, properties, namespaces, and mappings. It also
    supports operations like adding terms, namespaces, and generating a networkx
    graph representation of the ontology.

    graph : rdflib.Graph
        The RDF graph containing the ontology data.

    Attributes
    graph : rdflib.Graph
        The RDF graph containing the ontology data.
    _data_dict : dict or None
        A dictionary to store parsed ontology data. Initialized lazily.
    classes : list
        A list of ontology classes extracted from the graph.
    mappings : dict
        A dictionary of mappings for ontology terms, including unions and intersections.
    namespaces : dict
        A dictionary of namespaces extracted from the graph.
    extra_namespaces : dict
        A dictionary of additional namespaces.
    attributes : dict
        A dictionary containing attributes of classes, object properties, data properties,
        and data nodes.
    base_iri : str or None
        The base IRI of the ontology, if available.
    """
    def __init__(self, graph):
        self.graph = graph
        self._data_dict = None

    def _initialize(self):
        self._data_dict = {
            "classes": [],
            "attributes": {
                "class": {},
                "object_property": {},
                "data_property": {},
                "data_nodes": {},
            },
            "mappings": {},
            "namespaces": {},
            "extra_namespaces": {},
        }
        self._extract_default_namespaces()
        self.extract_classes()
        self.add_classes_to_attributes()
        self.parse_subclasses()
        self.recursively_add_subclasses()
        self.add_subclasses_to_owlThing()
        self.parse_equivalents()
        self.recursively_add_equivalents()
        self.parse_named_individuals()
        self.extract_object_properties()
        self.extract_data_properties()
        self.extract_subproperties()
        self.recheck_namespaces()

    @property
    def classes(self):
        return self.data_dict["classes"]

    @property
    def mappings(self):
        return self.data_dict["mappings"]

    @property
    def namespaces(self):
        return self.data_dict["namespaces"]

    @property
    def extra_namespaces(self):
        return self.data_dict["extra_namespaces"]

    @property
    def attributes(self):
        return self.data_dict["attributes"]

    @property
    def data_dict(self):
        if self._data_dict is None:
            self._initialize()
        return self._data_dict

    def __add__(self, ontoparser):
        """
        Combine the graphs of two OntoParser instances.

        This method allows the addition of another OntoParser instance's graph
        to the current instance's graph, resulting in a new OntoParser instance
        with the combined graph.

        Parameters
        ----------
        ontoparser : OntoParser
            Another instance of OntoParser whose graph will be added to the
            current instance's graph.

        Returns
        -------
        OntoParser
            A new OntoParser instance containing the combined graph of the
            current instance and the provided OntoParser instance.

        """
        graph = self.graph + ontoparser.graph
        return OntoParser(graph)

    def __radd__(self, ontoparser):
        return self.__add__(ontoparser)

    @property
    def base_iri(self):
        base_iri = None
        for s in self.graph.subjects(RDF.type, OWL.Ontology):
            base_iri = str(s)
        return base_iri

    def _extract_default_namespaces(self):
        """
        Extracts and stores non-default namespaces from the RDF graph.

        Iterates through the namespaces in the RDF graph and adds those with 
        non-empty prefixes that do not contain the word "default" to the 
        `self.namespaces` dictionary. The prefix is used as the key, and the 
        namespace URI (converted to a Python string) is used as the value.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        for prefix, namespace in self.graph.namespaces():
            if len(prefix) > 0 and "default" not in prefix:
                self.namespaces[prefix] = namespace.toPython()

    def recheck_namespaces(self):
        """
        Rechecks and updates the namespaces in the attributes.

        This method iterates through the specified keys in the `attributes` dictionary
        (e.g., "class", "object_property", "data_property") and ensures that the namespaces
        associated with these keys are present in the `namespaces` dictionary. If a namespace
        is not already in `namespaces`, it is added along with its corresponding prefix.
        """
        for mainkey in ["class", "object_property", "data_property"]:
            for key, val in self.attributes[mainkey].items():
                namespace = self.attributes[mainkey][key].namespace
                if namespace not in self.namespaces.keys():
                    self.namespaces[namespace] = self.attributes[mainkey][
                        key
                    ].namespace_with_prefix

    def extract_object_properties(self):
        """
        Extracts all object properties from the RDF graph and processes them.

        This method retrieves all object properties defined in the RDF graph
        that are of type `OWL.ObjectProperty`. For each object property, it
        creates a term, assigns its domain, range, and node type, and stores
        it in the `attributes` dictionary under the "object_property" key.
        """
        object_properties = list(self.graph.subjects(RDF.type, OWL.ObjectProperty))
        for cls in object_properties:
            term = self.create_term(cls)
            term.domain = self.get_domain(cls)
            term.range = self.get_range(cls)
            term.node_type = "object_property"
            self.attributes["object_property"][term.name] = term

    def extract_data_properties(self):
        """
        Extracts data properties from the RDF graph and processes them.

        This method identifies all data properties in the RDF graph, creates terms
        for each property, assigns their domain and range, and categorizes them as
        "data_property". Additionally, it creates associated data nodes for each
        data property and stores them in the attributes dictionary.
        """
        data_properties = list(self.graph.subjects(RDF.type, OWL.DatatypeProperty))
        for cls in data_properties:
            term = self.create_term(cls)
            term.domain = self.get_domain(cls)
            rrange = self.get_range(cls)
            rrange = [x.split(":")[-1] for x in rrange]
            rrange = patch_terms(term.uri, rrange)

            term.range = rrange
            term.node_type = "data_property"
            self.attributes["data_property"][term.name] = term

            # now create data nodes
            data_term = OntoTerm(name=term.name + "value", node_type="data_node")
            self.attributes["data_property"][
                term.name
            ].associated_data_node = data_term.name
            self.attributes["data_nodes"][data_term.name] = data_term

    def extract_subproperties(self):
        """
        Extracts and organizes subproperties for object and data properties in the RDF graph.

        This method processes the RDF graph to identify subproperties of both object and 
        data properties. It updates the `attributes` dictionary with the hierarchical 
        relationships between properties and recursively adds subclasses for each property.
        """
        top_most_properties = [OWL.topObjectProperty, OWL.topDataProperty]
        # we iterate over all object properties, and add the subproperties
        for prop_type in ["object_property", "data_property"]:
            for key, prop in self.attributes[prop_type].items():
                # get the subproperties
                top_props = list(self.graph.objects(prop.URIRef, RDFS.subPropertyOf))
                for top_prop in top_props:
                    if top_prop not in top_most_properties:
                        # get the name of the subproperty
                        toppropname = strip_name(top_prop.toPython())
                        # add it to the object property
                        self.attributes[prop_type][toppropname].subclasses.append(
                            prop.name
                        )
        # recursivly add the subproperties
        for prop_type in ["object_property", "data_property"]:
            for key, prop in self.attributes[prop_type].items():
                self._recursively_add_subclasses(key, item_type=prop_type)

    def extract_values(self, subject, predicate):
        """
        Extract the first value associated with a given subject and predicate 
        from the RDF graph.

        Parameters
        ----------
        subject : rdflib.term.Identifier
            The subject node in the RDF graph.
        predicate : rdflib.term.Identifier
            The predicate node in the RDF graph.

        Returns
        -------
        rdflib.term.Identifier or None
            The first object value associated with the given subject and predicate,
            or None if no such value exists.
        """
        for val in self.graph.objects(subject, predicate):
            return val
        return None

    def extract_classes(self):
        """
        Extracts OWL classes and their relationships from the RDF graph.

        This method iterates over all subjects in the RDF graph that are of type `OWL.Class`.
        It handles both named classes and anonymous classes (blank nodes). For anonymous
        classes, it identifies union and intersection relationships and maps them to their
        respective components. Named classes are directly added to the `classes` list.

        At the end, the `OWL.Thing` class is also added to the `classes` list.
        """
        for term in self.graph.subjects(RDF.type, OWL.Class):
            if isinstance(term, BNode):
                for relation_type, owl_term in [
                    ("union", OWL.unionOf),
                    ("intersection", OWL.intersectionOf),
                ]:
                    union_term = self.extract_values(term, owl_term)
                    if union_term is not None:
                        unravel_list = self.unravel_relation(union_term)
                        self.mappings[term.toPython()] = {
                            "type": relation_type,
                            "items": [
                                strip_name(item.toPython()) for item in unravel_list
                            ],
                        }
            else:
                self.classes.append(term)
        self.classes.append(OWL.Thing)

    def add_classes_to_attributes(self):
        """
        Adds classes to the attributes dictionary under the "class" key.

        This method iterates over the `classes` attribute, creates a term for each class,
        assigns it a node type of "class", and stores it in the `attributes` dictionary
        under the "class" key, using the term's name as the key.
        """
        for cls in self.classes:
            term = self.create_term(cls)
            term.node_type = "class"
            self.attributes["class"][term.name] = term

    def get_description(self, cls):
        """
        Retrieve the description of a given class from the RDF graph.

        This method attempts to fetch the description of the specified class
        (`cls`) from the RDF graph. It first looks for a value associated with
        the IAO_0000115 property (a common property for textual definitions in
        ontologies). If no value is found, it falls back to the RDFS.comment
        property. If neither property has a value, an empty string is returned.

        Parameters
        ----------
        cls : rdflib.term.URIRef
            The RDF class (URIRef) for which the description is to be retrieved.

        Returns
        -------
        str
            The description of the class, or an empty string if no description
            is found.
        """
        comment = self.graph.value(
            cls, URIRef("http://purl.obolibrary.org/obo/IAO_0000115")
        )
        if comment is None:
            comment = self.graph.value(cls, RDFS.comment)
        if comment is None:
            comment = ""
        return comment

    def lookup_node(self, term):
        """
        Maps a given term to its corresponding domain, range, and related hierarchies.

        This method processes a term (either a blank node or a named node) and retrieves 
        its associated mappings, subclasses, equivalent classes, and named individuals 
        from the class attributes. The resulting terms include the original term and 
        any additional terms derived from the hierarchy.

        Parameters
        ----------
        term : BNode or other
            The term to be looked up. It can be a blank node (BNode) or another type of term.

        Returns
        -------
        list
            A list of terms including the original term and any additional terms 
            derived from the hierarchy (subclasses, equivalent classes, and named individuals).

        """
        if isinstance(term, BNode):
            # lookup needed
            term_name = term.toPython()
            if term_name in self.mappings:
                terms = self.mappings[term_name]["items"]
            else:
                terms = [strip_name(term.toPython())]
        else:
            terms = [strip_name(term.toPython())]
        # so here we map the domain and range wrt to other heirarchies
        additional_terms = []
        # first get subclasses which will share the domain and range
        for term in terms:
            # check if such a thing exists in the class
            if term in self.attributes["class"]:
                # get the subclasses
                additional_terms += self.attributes["class"][term].subclasses
                # get the equivalent classes
                additional_terms += self.attributes["class"][term].equivalent_classes
                # get the named individuals
                additional_terms += self.attributes["class"][term].named_individuals
        # add additiona terms to terms
        terms += additional_terms
        return terms

    def lookup_class(self, term):
        """
        Lookup the class associated with a given term.

        This method retrieves the class name(s) associated with the provided term
        by checking the `attributes["class"]` dictionary or the `mappings` dictionary.

        Parameters
        ----------
        term : Union[BNode, Any]
            The term to look up. It can be a `BNode` or any other type that has a
            `toPython()` method.

        Returns
        -------
        list
            A list containing the class name(s) associated with the term. If no
            class is found, an empty list is returned.
        """
        if isinstance(term, BNode):
            term = term.toPython()
        else:
            term = strip_name(term.toPython())
        # print(term)
        if term in self.attributes["class"]:
            return [self.attributes["class"][term].name]
        elif term in self.mappings:
            return self.mappings[term]["items"]
        else:
            return []

    def get_domain(self, cls):
        """
        Retrieve the domain of a given class.

        Parameters
        ----------
        cls : Any
            The class for which the domain is to be retrieved.

        Returns
        -------
        Any
            The domain associated with the given class.
        """
        return self._get_domain_range(cls, RDFS.domain)

    def get_range(self, cls):
        """
        Retrieves the range of a given class.

        Parameters
        ----------
        cls : object
            The class for which the range is to be retrieved.

        Returns
        -------
        object
            The range associated with the given class, as determined by the RDFS.range property.
        """
        return self._get_domain_range(cls, RDFS.range)

    def _get_domain_range(self, cls, predicate):
        """
        Retrieve the domain or range of a given predicate for a specified class.

        This method queries the RDF graph to find objects associated with the given
        class (`cls`) and predicate (`predicate`). It then resolves these objects
        into terms using the `lookup_node` method and returns them as a list.

        Parameters
        ----------
        cls : rdflib.term.Identifier
            The RDF class for which the domain or range is being retrieved.
        predicate : rdflib.term.Identifier
            The RDF predicate used to query the graph.

        Returns
        -------
        list
            A list of terms representing the domain or range of the given predicate
            for the specified class.
        """
        domain = []
        for obj in self.graph.objects(cls, predicate):
            domain_term = self.lookup_node(obj)
            for term in domain_term:
                domain.append(term)
        return domain

    def create_term(self, cls):
        """
        Create an OntoTerm instance for a given class.

        Parameters
        ----------
        cls : rdflib.term.Identifier
            The RDFLib class identifier for which the OntoTerm is to be created.

        Returns
        -------
        OntoTerm
            An instance of OntoTerm containing the URI, namespace, description, 
            and target class.

        Notes
        -----
        This method extracts the IRI from the given class, determines its namespace,
        retrieves its description, and creates an OntoTerm object encapsulating 
        these details.
        """
        iri = cls.toPython()
        term = OntoTerm(
            uri=iri,
            namespace=self._lookup_namespace(iri),
            description=self.get_description(cls),
            target=cls,
        )
        return term

    def _lookup_namespace(self, uri):
        """
        Look up the namespace prefix for a given URI.

        This method iterates through the stored namespaces and checks if the 
        provided URI starts with any of the namespace values. If a match is found, 
        the corresponding namespace prefix is returned.

        Parameters
        ----------
        uri : str
            The URI to be checked against the stored namespaces.

        Returns
        -------
        str or None
            The namespace prefix if a match is found, otherwise None.
        """
        for key, value in self.namespaces.items():
            if uri.startswith(value):
                return key
        return None

    def unravel_relation(self, term, unravel_list=[]):
        """
        Recursively unravels an RDF collection into a Python list.

        This method traverses an RDF collection starting from the given `term` 
        and extracts its elements into a Python list. The RDF collection is 
        expected to follow the structure defined by `RDF.first` and `RDF.rest`.

        Parameters
        ----------
        term : rdflib.term.Identifier
            The starting RDF term of the collection to unravel. Typically, this 
            is the head of the RDF list.
        unravel_list : list, optional
            A list to accumulate the elements of the RDF collection. Defaults 
            to an empty list.

        Returns
        -------
        list
            A Python list containing the elements of the RDF collection in the 
            order they appear.
        """
        if term == RDF.nil:
            return unravel_list
        first_term = self.graph.value(term, RDF.first)
        if first_term not in unravel_list:
            unravel_list.append(first_term)
        second_term = self.graph.value(term, RDF.rest)
        return self.unravel_relation(second_term, unravel_list)

    def parse_subclasses(self):
        """
        Parses and processes subclass relationships in the RDF graph.

        This method iterates over the classes defined in the `attributes["class"]` 
        dictionary and identifies their superclasses by examining the RDF graph. 
        It then updates the `subclasses` attribute of each superclass to include 
        the current class.
        """
        for key, cls in self.attributes["class"].items():
            for obj in self.graph.objects(cls.target, RDFS.subClassOf):
                superclasses = self.lookup_class(obj)
                for superclass in superclasses:
                    self.attributes["class"][superclass].subclasses.append(cls.name)

    def recursively_add_subclasses(self, item_type="class"):
        """
        Recursively adds subclasses for each class in the specified item type.

        This method iterates through all the classes in the specified item type
        and calls a helper method to recursively add their subclasses.

        Parameters
        ----------
        item_type : str, optional
            The type of item to process (default is "class"). This is used to
            determine which set of attributes to process.
        """
        for clsname in self.attributes[item_type].keys():
            self._recursively_add_subclasses(clsname, item_type=item_type)

    def _recursively_add_subclasses(self, clsname, item_type="class"):
        """
        Recursively adds all subclasses of a given class to its subclass list.

        This method traverses the subclass hierarchy for a given class and ensures
        that all indirect subclasses are added to the direct subclass list of the
        specified class.

        Parameters
        ----------
        clsname : str
            The name of the class whose subclass hierarchy is to be processed.
        item_type : str, optional
            The type of item being processed (default is "class").
        """
        subclasses_to_add = []
        for subclass in self.attributes[item_type][clsname].subclasses:
            for subclass_of_subclass in self.attributes[item_type][subclass].subclasses:
                if (
                    subclass_of_subclass
                    not in self.attributes[item_type][clsname].subclasses
                ):
                    subclasses_to_add.append(subclass_of_subclass)
        if len(subclasses_to_add) == 0:
            return
        self.attributes[item_type][clsname].subclasses.extend(subclasses_to_add)
        self._recursively_add_subclasses(clsname, item_type=item_type)

    def add_subclasses_to_owlThing(self):
        """
        Adds subclasses to the "owl:Thing" class if they do not already have a superclass.

        This method iterates through all classes in the `attributes["class"]` dictionary.
        For each class, it checks if the class has any existing `rdfs:subClassOf` relationships
        in the RDF graph. If no such relationships are found, the class is added as a subclass
        of "owl:Thing".
        """
        for key, cls in self.attributes["class"].items():
            objects = list(self.graph.objects(cls.target, RDFS.subClassOf))
            if len(objects) == 0:
                self.attributes["class"]["owl:Thing"].subclasses.append(cls.name)

    def parse_equivalents(self):
        """
        Parses and updates equivalent classes in the RDF graph.

        This method iterates through the classes in the `attributes["class"]` 
        dictionary and identifies equivalent classes using the OWL.equivalentClass 
        predicate in the RDF graph. For each equivalent class found, it updates 
        the `equivalent_classes` attribute of both the current class and its 
        equivalent class.
        """
        for key, cls in self.attributes["class"].items():
            for equivalent in self.graph.objects(cls.target, OWL.equivalentClass):
                if strip_name(equivalent) in self.attributes["class"]:
                    self.attributes["class"][
                        strip_name(equivalent)
                    ].equivalent_classes.append(cls.name)
                    cls.equivalent_classes.append(strip_name(equivalent))

    def recursively_add_equivalents(self):
        """
        Recursively adds equivalent classes to the attributes dictionary.

        This method iterates through all class names in the "class" attribute
        and calls a helper method to recursively add equivalent classes for
        each class name.
        """
        for clsname in self.attributes["class"].keys():
            self._recursively_add_equivalents(clsname)

    def _recursively_add_equivalents(self, clsname):
        """
        Recursively adds all equivalent classes for a given class.

        This method ensures that all transitive equivalent classes of the 
        specified class are added to its list of equivalent classes. It 
        traverses the equivalence relationships and updates the class 
        attributes accordingly.

        Parameters
        ----------
        clsname : str
            The name of the class for which equivalent classes are to be added.
        """
        equivalents_to_add = []
        for equivalent in self.attributes["class"][clsname].equivalent_classes:
            for equivalent_of_equivalent in self.attributes["class"][
                equivalent
            ].equivalent_classes:
                if (
                    equivalent_of_equivalent
                    not in self.attributes["class"][clsname].equivalent_classes
                ):
                    equivalents_to_add.append(equivalent_of_equivalent)
        if len(equivalents_to_add) == 0:
            return
        self.attributes["class"][clsname].equivalent_classes.extend(equivalents_to_add)
        self._recursively_add_equivalents(clsname)

    def parse_named_individuals(self):
        """
        Parses named individuals from the RDF graph and updates the attributes.

        This method identifies all named individuals in the RDF graph, creates
        corresponding terms, and associates them with their parent classes. The
        parsed information is stored in the `attributes` dictionary under the
        "class" key.
        """
        named_individuals = list(self.graph.subjects(RDF.type, OWL.NamedIndividual))
        for cls in named_individuals:
            # find parent
            term = self.create_term(cls)
            self.attributes["class"][term.name] = term
            parents = list(self.graph.objects(cls, RDF.type))
            for parent in parents:
                if parent not in [OWL.NamedIndividual, OWL.Class]:
                    self.attributes["class"][
                        strip_name(parent.toPython())
                    ].named_individuals.append(term.name)

    def get_attributes(self):
        """
        Constructs a mapping of attributes grouped by their namespaces.

        This method processes the attributes of classes, object properties, and 
        data properties, organizing them into a dictionary where the keys are 
        namespaces and the values are dictionaries of attributes belonging to 
        those namespaces.

        Returns
        -------
        dict
            A dictionary where each key is a namespace (str), and the value is 
            another dictionary. The inner dictionary maps attribute names 
            (without prefixes) to their corresponding attribute objects.
        """
        # add first level - namespaces
        namespaces = []
        for k1 in ["class", "object_property", "data_property"]:
            for k2, val in self.attributes[k1].items():
                if val.namespace not in namespaces:
                    namespaces.append(val.namespace)
        mapdict = {key: {} for key in namespaces}

        # now iterate over all attributes
        for k1 in ["class", "object_property", "data_property"]:
            for k2, val in self.attributes[k1].items():
                mapdict[val.namespace][val.name_without_prefix] = val
        return mapdict

    def get_networkx_graph(self):
        """
        Constructs a directed graph representation of the ontology using NetworkX.

        This method creates a directed graph (`DiGraph`) where nodes represent 
        classes, object properties, and data properties, and edges represent 
        relationships between them. The graph is built based on the `attributes` 
        dictionary of the object, which contains information about classes, 
        object properties, and data properties.

        Returns
        -------
        networkx.DiGraph
            A directed graph where:
            - Nodes are labeled with their names and have a `node_type` attribute 
              indicating whether they are a "class", "object_property", or 
              "data_property".
            - Edges represent relationships between classes and properties, 
              including domains and ranges.
        """
        g = nx.DiGraph()
        for key, val in self.attributes["class"].items():
            g.add_node(val.name, node_type="class")

        for property_key in ["object_property", "data_property"]:
            for key, val in self.attributes[property_key].items():
                g.add_node(val.name, node_type=property_key)

                # add edges between them
                for d in val.domain:
                    g.add_edge(d, val.name)

                if property_key == "object_property":
                    for r in val.range:
                        g.add_edge(val.name, r)
                else:
                    g.add_edge(val.name, val.associated_data_node)
        return g

    def add_term(
        self,
        uri,
        node_type,
        namespace=None,
        dm=(),
        rn=(),
        data_type=None,
        node_id=None,
        delimiter="/",
    ):
        """
        Add a node.

        Parameters
        ----------
        uri : str
            The URI of the node.
        node_type : str
            The type of the node.
        namespace : str, optional
            The namespace of the node.
        dm : list, optional
            The domain metadata of the node.
        rn : list, optional
            The range metadata of the node.
        data_type : str, optional
            The data type of the node.
        node_id : str, optional
            The ID of the node.
        delimiter : str, optional
            The delimiter used for parsing the URI.

        Raises
        ------
        ValueError
            If the namespace is not found.

        """
        if node_type == "class":
            self.graph.add((URIRef(uri), RDF.type, OWL.Class))
        elif node_type == "object_property":
            self.graph.add((URIRef(uri), RDF.type, OWL.ObjectProperty))
        elif node_type == "data_property":
            self.graph.add((URIRef(uri), RDF.type, OWL.DatatypeProperty))
        else:
            raise ValueError("Node type not found")
        for r in rn:
            self.graph.add((URIRef(uri), RDFS.range, URIRef(r)))
        for d in dm:
            self.graph.add((URIRef(uri), RDFS.domain, URIRef(d)))
        self._data_dict = None

    def add_namespace(self, namespace_name, namespace_iri):
        """
        Add a new namespace.

        Parameters
        ----------
        namespace_name : str
            The name of the namespace to add.
        namespace_iri : str
            The IRI of the namespace.

        Raises
        ------
        KeyError
            If the namespace already exists.

        """
        if namespace_name not in self.namespaces.keys():
            self.graph.bind(namespace_name, namespace_iri)
        self._data_dict = None
