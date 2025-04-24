"""
This module provides a network representation of ontologies, enabling operations such as
query generation, shortest path computation, and visualization of ontology graphs.

Features:
- Generate SPARQL queries based on ontology structure and relationships.
- Compute shortest paths between ontology terms.
- Visualize ontology graphs using Graphviz.
- Extend and manipulate ontology networks with additional namespaces, terms, and paths.
"""

import networkx as nx
import graphviz
import pandas as pd
import itertools

from rdflib import URIRef, Literal, RDF, OWL
from tools4rdf.network.attrsetter import AttrSetter
from tools4rdf.network.parser import parse_ontology, OntoParser


def _replace_name(name):
    return ".".join(name.split(":"))


def _strip_name(name):
    raw = name.split(":")
    if len(raw) > 1:
        return raw[-1]
    return name


class Network:
    """
    Network
    -------
    A class for representing and interacting with a network graph derived from an ontology. 
    This class provides methods for visualizing the graph, computing shortest paths, 
    and generating SPARQL queries based on the graph structure.

    Attributes
    ----------

    terms : AttrSetter
        An object for managing attributes of the ontology terms.
    g : networkx.Graph
        The NetworkX graph representation of the ontology.
    namespaces : dict
        A dictionary of namespaces defined in the ontology.
    extra_namespaces : dict
        Additional namespaces that are not part of the core ontology.

    Methods
    -------

    draw(styledict=None)
        Draw the network graph using Graphviz with customizable styles for node types.
    _get_shortest_path(source, target, num_paths=1)
        Compute the shortest path(s) between two nodes in the graph.
    get_shortest_path(source, target, triples=False, num_paths=1)
        Compute the shortest path(s) between two nodes, optionally returning the path as triples.
    _insert_namespaces(namespaces)
        Insert namespace prefixes into a SPARQL query.
    create_query(source, destinations=None, return_list=False, num_paths=1)
        Generate SPARQL queries based on the source and destination nodes.
    _prepare_destinations(destinations=None)
        Prepare and validate destination nodes for query generation.
    _create_query_prefix(source, destinations)
        Create the prefix and SELECT clause for a SPARQL query.
    _get_triples(source, destinations, num_paths=1)
        Generate triples for SPARQL queries based on paths between source and destination nodes.
    _add_types_for_source(source)
        Add type constraints for the source node in a SPARQL query.
    _add_types_for_destination(destinations)
        Add type constraints for the destination nodes in a SPARQL query.
    _add_filters(destinations)
        Add filter conditions to a SPARQL query based on destination nodes.
    _create_query(source, destinations=None, num_paths=1)
        Generate a complete SPARQL query string based on the source and destination nodes.
    query(kg, source, destinations=None, return_df=True, num_paths=1)
        Execute SPARQL queries on a knowledge graph and return the results.
    _query(kg, query_string, return_df=True)
        Execute a single SPARQL query on a knowledge graph and return the results.
    """
    def __init__(self, onto):
        self.terms = AttrSetter()
        self.terms._add_attribute(onto.get_attributes())
        self.g = onto.get_networkx_graph()
        self.namespaces = onto.namespaces
        self.extra_namespaces = onto.extra_namespaces

    def draw(
        self,
        styledict={
            "class": {"shape": "box"},
            "object_property": {"shape": "ellipse"},
            "data_property": {"shape": "ellipse"},
            "literal": {"shape": "parallelogram"},
        },
    ):
        """
        Draw the network graph using graphviz.

        Parameters
        ----------
        styledict : dict, optional
            A dictionary specifying the styles for different node types.
            The keys of the dictionary are the node types, and the values are dictionaries
            specifying the shape for each node type. Defaults to None.

        Returns
        -------
        graphviz.Digraph
            The graph object representing the network graph.

        Example
        -------
        styledict = {
            "class": {"shape": "box"},
            "object_property": {"shape": "ellipse"},
            "data_property": {"shape": "ellipse"},
            "literal": {"shape": "parallelogram"},
        }
        network.draw(styledict)
        """
        dot = graphviz.Digraph()
        node_list = list(self.g.nodes(data="node_type"))
        edge_list = list(self.g.edges)
        for node in node_list:
            name = _replace_name(node[0])
            if node[1] is not None:
                t = node[1]
                dot.node(name, shape=styledict[t]["shape"], fontsize="6")
        for edge in edge_list:
            dot.edge(_replace_name(edge[0]), _replace_name(edge[1]))
        return dot

    def _get_shortest_path(self, source, target, num_paths=1):
        """
        Compute the shortest paths between two nodes in a graph.

        This method finds the shortest paths between a source and target node 
        in the graph `self.g` using their `query_name` attributes. The resulting 
        paths are modified to replace the start and end nodes with their 
        corresponding variable names.

        Parameters
        ----------
        source : OntoTerm
            The source node, represented as an OntoTerm object. The `query_name` 
            attribute is used to identify the node in the graph, and the 
            `variable_name` attribute is used to replace the start node in the path.
        target : OntoTerm
            The target node, represented as an OntoTerm object. The `query_name` 
            attribute is used to identify the node in the graph, and the 
            `variable_name` attribute is used to replace the end node in the path.
            If the `node_type` of the target is "object_property", the 
            `variable_name` is appended to the path; otherwise, it replaces the 
            last node in the path.
        num_paths : int, optional
            The maximum number of shortest paths to compute (default is 1).

        Returns
        -------
        list of list
            A list of shortest paths, where each path is represented as a list of 
            nodes. The start and end nodes in each path are replaced with their 
            corresponding variable names.

        Notes
        -----
        - This method uses the `networkx.shortest_simple_paths` function to 
          compute the paths.
        """
        # this function will be modified to take OntoTerms direcl as input; and use their names.
        path_iterator = nx.shortest_simple_paths(
            self.g, source=source.query_name, target=target.query_name
        )
        # replace the start and end with thier corresponding variable names
        paths = []
        for count, path in enumerate(path_iterator):
            if count == num_paths:
                break
            path = list(path)
            # now we need to replace the start and end with their variable names
            path[0] = source.variable_name
            if target.node_type == "object_property":
                path.append(target.variable_name)
            else:
                path[-1] = target.variable_name
            paths.append(path)
        return paths

    def get_shortest_path(self, source, target, triples=False, num_paths=1):
        """
        Computes the shortest path(s) between a source and target node in a network.

        If the target node has parent nodes, the function computes a stepped query
        that includes paths through the parent nodes. Otherwise, it computes the
        shortest path directly between the source and target.

        Parameters
        ----------
        source : Node
            The starting node for the path computation.
        target : Node
            The destination node for the path computation.
        triples : bool, optional
            If True, the function returns the paths as lists of triples (default is False).
        num_paths : int, optional
            The number of shortest paths to compute (default is 1). Only used if it is not a 
            stepped query.

        Returns
        -------
        list
            If `triples` is False, returns a list of nodes representing the shortest path(s).
            If `triples` is True, returns a list of lists, where each inner list contains
            triples representing the path(s).

        Notes
        -----
        - If the target node has parent nodes, the function computes a stepped query
          by combining paths between consecutive nodes in the sequence: source -> parent1 -> ... -> target.
        """
        # this function should also check for stepped queries
        paths = []
        if len(target._parents) > 0:
            # this needs a stepped query
            complete_list = [source, *target._parents, target]
            # get path for first two terms
            path = self._get_shortest_path(complete_list[0], complete_list[1])
            for x in range(2, len(complete_list)):
                temp_source = complete_list[x - 1]
                temp_dest = complete_list[x]
                temp_path = self._get_shortest_path(temp_source, temp_dest)
                if len(temp_path) == 2:
                    # this means that they are next to each other, so we cannot form a full path
                    # so we need to add the last item of the previous path
                    path[-1] = temp_path[-1]
                else:
                    path.extend(temp_path[1:])
            paths.extend(path)
        else:
            paths = self._get_shortest_path(source, target, num_paths=num_paths)
        if triples:
            triple_lists = []
            for path in paths:
                triple_list = []
                for x in range(len(path) // 2):
                    triple_list.append(path[2 * x : 2 * x + 3])
                triple_lists.append(triple_list)
            return triple_lists

        return paths

    def _insert_namespaces(self, namespaces):
        """
        Constructs a list of SPARQL PREFIX declarations for the given namespaces.

        Parameters
        ----------
        namespaces : dict
            A dictionary where keys are namespace prefixes and values are their corresponding URIs.

        Returns
        -------
        list of str
            A list of SPARQL PREFIX declarations in the format "PREFIX prefix: <URI>".

        Notes
        -----
        This method combines the instance's `namespaces` and `extra_namespaces` attributes
        to resolve the URIs for the provided namespace prefixes.
        """
        query = []
        ns = self.namespaces | self.extra_namespaces
        for key in namespaces:
            query.append(f"PREFIX {key}: <{ns[key]}>")
        return query

    def create_query(self, source, destinations=None, return_list=False, num_paths=1):
        """
        Creates a query based on the given source and destination nodes.

        Parameters
        ----------
        source : list or object
            The source nodes for the query. If not a list, it will be converted to a list.
            Each source node must not be of type "data_property".
        destinations : list, object, or None, optional
            The destination nodes for the query. If not a list, it will be converted to a list.
            If None, the query will only consider the source nodes. Default is None.
        return_list : bool, optional
            If True, the function will return a list of queries. If False, it will return a single query
            if only one query is generated. Default is False.
        num_paths : int, optional
            The number of paths to consider in the query. Default is 1.

        Raises
        ------
        ValueError
            If any source node is of type "data_property".
            If no common classes are found in the domains of the object properties.

        Returns
        -------
        list or object
            A list of queries if `return_list` is True or multiple queries are generated.
            A single query if `return_list` is False and only one query is generated.
        """
        # we need to handle source and destination, the primary aim here is to handle source
        if not isinstance(source, list):
            source = [source]
        if destinations is not None:
            if not isinstance(destinations, list):
                destinations = [destinations]
        # if any of the source items are data properties, fail
        for s in source:
            if s.node_type == "data_property":
                raise ValueError("Data properties are not allowed as source nodes.")

        # separate sources into classes and object properties
        classes = []
        object_properties = []
        for s in source:
            if s.node_type == "class":
                classes.append(s)
            elif s.node_type == "object_property":
                object_properties.append(s)

        # now one has to reduce the object properties, this can be done by finding
        # common classes in the domains
        # Do only if we have object properties
        if len(object_properties) > 0:
            domains = [a.domain for a in object_properties]
            common_classes = set(domains[0])
            for d in domains[1:]:
                common_classes = common_classes.intersection(set(d))
            # now if we do not have any common classes, raise an error
            common_classes = [self.onto.attributes["class"][x] for x in common_classes]
            if len(common_classes) == 0:
                raise ValueError(
                    "No common classes found in the domains of the object properties."
                )

            # now check classes; see if anython common classes are not there, if so add.
            # we just need one common class, these queries will NOT be type fixed
            common_class = common_classes[0]
            class_names = [c.name for c in classes]
            if common_class.name not in class_names:
                classes.append(common_class.any)

        # the pplan is to phase out the @ operator, so we look for lists within destinations
        if destinations is not None:
            modified_destinations = []
            for count, destination in enumerate(destinations):
                if isinstance(destination, (list, tuple)):
                    last_destination = destination[-1]
                    for d in destination[:-1]:
                        last_destination._parents.append(d)
                    modified_destinations.append(last_destination)
                else:
                    modified_destinations.append(destination)
            destinations = modified_destinations

        # now classes are the new source nodes
        # object propertiues are ADDED to the destination nodes
        source = classes
        if destinations is not None:
            if not isinstance(destinations, list):
                destinations = [destinations]
            for object_property in object_properties:
                already_there = False
                if object_property in destinations:
                    already_there = True
                for d in destinations:
                    if object_property in d._parents:
                        already_there = True
                if not already_there:
                    destinations.append(object_property)
        elif len(object_properties) > 0:
            destinations = object_properties

        if destinations is None:
            destinations = []

        # done, now run the query
        queries = []
        for s in source:
            queries.extend(
                self._create_query(s, destinations=destinations, num_paths=num_paths)
            )

        if (len(queries) == 1) and not return_list:
            return queries[0]
        return queries

    def _prepare_destinations(self, destinations=None):
        """
        Prepares and validates the list of destination objects.

        This method ensures that the provided destinations meet specific conditions
        and adds any necessary parent destinations based on their conditions.

        Parameters
        ----------
        destinations : list, optional
            A list of destination objects to be prepared. If None, the method checks
            if `source._enforce_type` is enabled and raises a ValueError if it is not.

        Returns
        -------
        list
            A modified list of destination objects, including any necessary parent
            destinations.

        Raises
        ------
        ValueError
            If `destinations` is None and `source.any` is used without enforcing type.
        ValueError
            If more than one destination has an associated condition.
        """
        if destinations is None and not source._enforce_type:
            raise ValueError(
                "If no destinations are provided, source.any cannot be used!."
            )

        # check if more than one of them have an associated condition -> if so throw error
        no_of_conditions = 0
        for destination in destinations:
            if destination._condition is not None:
                no_of_conditions += 1
        if no_of_conditions > 1:
            raise ValueError("Only one condition is allowed")

        # iterate through the list, if they have condition parents, add them explicitely
        for destination in destinations:
            for parent in destination._condition_parents:
                if parent.variable_name not in [d.variable_name for d in destinations]:
                    destinations.append(parent)
        return destinations

    def _create_query_prefix(self, source, destinations):
        """
        Constructs the prefix of a SPARQL query with a SELECT DISTINCT clause.

        This method generates the initial part of a SPARQL query, including the 
        SELECT DISTINCT clause and the opening of the WHERE block. It includes 
        the source variable and a list of destination variables in the SELECT 
        clause.

        Parameters
        ----------
        source : object
            The source object, which must have a `variable_name` attribute 
            representing its SPARQL variable name.
        destinations : list of objects
            A list of destination objects, each of which must have a 
            `variable_name` attribute representing its SPARQL variable name.

        Returns
        -------
        list of str
            A list of strings representing the initial lines of the SPARQL query, 
            including the SELECT DISTINCT clause and the opening of the WHERE block.
        """
        # all names are now collected, in a list of lists
        # start prefix of query
        query = []

        # construct the select distinct command:
        # add source `variable_name`
        # iterate over destinations, add their `variable_name`
        select_destinations = [
            "?" + destination.variable_name for destination in destinations
        ]
        select_destinations = ["?" + source.variable_name] + select_destinations
        query.append(f'SELECT DISTINCT {" ".join(select_destinations)}')
        query.append("WHERE {")
        return query

    def _get_triples(self, source, destinations, num_paths=1):
        """
        Generate SPARQL queries and namespaces based on the shortest paths between a source and multiple destinations.

        For each source-destination pair, this method finds the shortest paths (up to `num_paths` paths) and combines 
        the resulting triples into SPARQL queries. It also extracts namespaces from the triples.

        Parameters
        ----------
        source : str
            The starting node for the paths.
        destinations : list of str
            A list of destination nodes for which paths need to be computed.
        num_paths : int, optional
            The number of shortest paths to compute for each source-destination pair (default is 1).

        Returns
        -------
        queries : list of list of str
            A list of SPARQL queries, where each query is represented as a list of triple patterns.
        namespaces : list of str
            A list of namespaces extracted from the triples.
        """
        # for each source and destinations, we need to find num_paths paths
        # then these have to be combined; and each set to be made into individual queries
        complete_triples = []
        for count, destination in enumerate(destinations):
            triplets = self.get_shortest_path(
                source, destination, triples=True, num_paths=num_paths
            )
            complete_triples.append(triplets)
        # flattened = [[item[0] for item in group] for group in complete_triples]
        # Get Cartesian product (all combinations)
        prepared = [[triple for triple in group] for group in complete_triples]
        # Get all combinations
        combinations = list(itertools.product(*prepared))
        namespaces = []
        queries = []

        for count, combination in enumerate(combinations):
            query = []
            namespace = []
            for triples in combination:
                for triple in triples:
                    namespace.extend([x.split(":")[0] for x in triple if ":" in x])
                    line_text = "    ?%s %s ?%s ." % (
                        triple[0].replace(":", "_"),
                        triple[1],
                        triple[2].replace(":", "_"),
                    )
                    if line_text not in query:
                        query.append(line_text)
            queries.append(query)
            namespaces.extend(namespace)

        return queries, namespaces

    def _add_types_for_source(self, source):
        """
        Constructs SPARQL query fragments to add type constraints for a given source node.

        This method generates query fragments to enforce RDF type constraints for a source node
        in a SPARQL query. It handles cases where subclasses need to be included or where a 
        specific type constraint is enforced.

        Parameters
        ----------
        source : object
            The source node object containing information about the node type, variable name, 
            query name, and additional attributes such as subclasses or type enforcement flags.

        Returns
        -------
        tuple
            A tuple containing:
            - query : list of str
                A list of SPARQL query fragments representing the type constraints.
            - namespaces_used : list of str
                A list of namespace prefixes used in the query fragments.
        """
        query = []
        namespaces_used = []
        if source._add_subclass and source.node_type == "class":
            # we have to make a type query connection by union
            query.append(
                "   { ?%s rdf:type %s . }"
                % (_strip_name(source.variable_name), source.query_name)
            )
            for cls_name in source.subclasses:
                if cls_name.split(":")[0] not in namespaces_used:
                    namespaces_used.append(cls_name.split(":")[0])

                query.append("    UNION    ")
                cls_term = self.attributes["class"][cls_name]
                query.append(
                    "   { ?%s rdf:type %s . }"
                    % (_strip_name(cls_term.variable_name), cls_term.query_name)
                )
        elif source._enforce_type and source.node_type == "class":
            query.append(
                "    ?%s rdf:type %s ."
                % (_strip_name(source.variable_name), source.query_name)
            )
        return query, namespaces_used

    def _add_types_for_destination(self, destinations):
        """
        Constructs SPARQL query fragments to add type information for the given destinations.

        This method generates SPARQL query fragments to enforce or add type relationships 
        for RDF nodes based on the provided `destinations`. It handles both subclass 
        relationships and enforced type constraints.

        Parameters
        ----------
        destinations : list
            A list of destination objects. Each destination object is expected to have 
            attributes such as `_add_subclass`, `_enforce_type`, `node_type`, `variable_name`, 
            `query_name`, and `subclasses`.

        Returns
        -------
        tuple
            A tuple containing:
            - query : list
                A list of SPARQL query fragments as strings.
            - namespaces_used : list
                A list of unique namespace prefixes used in the query.
        """
        query = []
        namespaces_used = []
        for destination in destinations:
            if destination._add_subclass and destination.node_type == "class":
                # we have to make a type query connection by union
                query.append(
                    "   { ?%s rdf:type %s . }"
                    % (_strip_name(destination.variable_name), destination.query_name)
                )
                for cls_name in destination.subclasses:
                    if cls_name.split(":")[0] not in namespaces_used:
                        namespaces_used.append(cls_name.split(":")[0])

                    query.append("    UNION    ")
                    cls_term = self.attributes["class"][cls_name]
                    query.append(
                        "   { ?%s rdf:type %s . }"
                        % (_strip_name(cls_term.variable_name), cls_term.query_name)
                    )

            elif destination._enforce_type and destination.node_type == "class":
                query.append(
                    "    ?%s rdf:type %s ."
                    % (
                        destination.variable_name,
                        destination.query_name,
                    )
                )
        return query, namespaces_used

    def _add_filters(self, destinations):
        """
        Adds filter conditions to a SPARQL query based on the provided destinations.

        This method processes a list of destination objects, extracts their filter
        conditions, and constructs a SPARQL query fragment with the appropriate
        FILTER clause. It also replaces query names with variable names in the
        filter conditions and ensures that the destination objects are refreshed
        after processing.

        Parameters
        ----------
        destinations : list
            A list of destination objects, each of which may contain a `_condition`
            attribute (representing a filter condition), `query_name` (the name of
            the query), and `variable_name` (the corresponding variable name).

        Returns
        -------
        list
            A list of strings representing the SPARQL query fragment, including
            the FILTER clause and a closing brace.
        """
        filter_text = ""
        query = []
        for destination in destinations:
            if destination._condition is not None:
                filter_text = destination._condition
                break

        # replace the query_name with variable_name
        if filter_text != "":
            for destination in destinations:
                filter_text = filter_text.replace(
                    destination.query_name, destination.variable_name
                )
            query.append(f"FILTER {filter_text}")
        query.append("}")

        # finished, clean up the terms;
        for destination in destinations:
            destination.refresh()
        return query

    def _create_query(self, source, destinations=None, num_paths=1):
        """
        Creates SPARQL queries based on the given source, destinations, and number of paths.

        This method generates SPARQL queries by preparing the destinations, constructing
        query headers, adding namespaces, and appending filters and type information for
        both the source and destinations.

        Parameters
        ----------
        source : object
            The source node for the query. It is expected to have a `name` attribute
            that includes a namespace prefix (e.g., "prefix:localName").
        destinations : list, optional
            A list of destination nodes for the query. If not provided, defaults to None.
        num_paths : int, optional
            The number of paths to include in the query. Defaults to 1.

        Returns
        -------
        list of str
            A list of SPARQL query strings generated based on the input parameters.

        Notes
        -----
        - The method internally handles namespace extraction and ensures that all
          required namespaces are included in the query.
        - Filters and type information are added to the query to refine the results.
        """

        destinations = self._prepare_destinations(destinations=destinations)
        query_header = self._create_query_prefix(source, destinations)

        namespaces_used = []
        # add the source to the namespaces
        namespaces_used.append(source.name.split(":")[0])
        namespaces_used.append("rdf")

        # get a list of queries
        queries, namespaces = self._get_triples(
            source, destinations, num_paths=num_paths
        )

        query_footer_source_types, namespaces_source = self._add_types_for_source(
            source
        )
        query_footer_dest_types, namespaces_dest = self._add_types_for_destination(
            destinations
        )

        query_filter = self._add_filters(destinations)

        created_queries = []
        for query in queries:
            query_header_new = (
                self._insert_namespaces(
                    set(
                        namespaces_used
                        + namespaces
                        + namespaces_source
                        + namespaces_dest
                    )
                )
                + query_header
            )
            query = (
                query_header_new
                + query
                + query_footer_source_types
                + query_footer_dest_types
                + query_filter
            )
            created_queries.append("\n".join(query))
        return created_queries

    def query(self, kg, source, destinations=None, return_df=True, num_paths=1):
        """
        Executes queries on a knowledge graph (KG) to retrieve data from a SPARQL query.

        Parameters
        ----------
        kg : object
            The knowledge graph object to query.
        source : OntoTerm
            The source node from which paths are to be queried.
        destinations : list of OntoTerm, optional
            A list of destination nodes to which paths are to be queried. If None, queries will not be restricted to specific destinations.
        return_df : bool, default=True
            If True, the results will be returned as a concatenated pandas DataFrame. Otherwise, results will be returned as a list.
        num_paths : int, default=1
            The number of paths to retrieve for each query.

        Returns
        -------
        pandas.DataFrame or list
            If `return_df` is True, returns a pandas DataFrame containing the query results.
            If `return_df` is False, returns a list of query results.
            Returns None if no results are found.
        """

        query_strings = self.create_query(
            source,
            destinations=destinations,
            return_list=True,
            num_paths=num_paths,
        )
        res = []
        for query_string in query_strings:
            r = self._query(kg, query_string, return_df=return_df)
            if r is not None:
                res.append(r)
        if len(res) == 0:
            return None
        if return_df:
            res = pd.concat(res)
        return res

    def _query(self, kg, query_string, return_df=True):
        """
        Executes a SPARQL query on the given knowledge graph (KG) and optionally 
        returns the result as a pandas DataFrame.

        Parameters
        ----------
        kg : object
            The knowledge graph object that supports the `query` method.
        query_string : str
            The SPARQL query string to be executed on the knowledge graph.
        return_df : bool, optional
            If True, the query result is returned as a pandas DataFrame. 
            Defaults to True.

        Returns
        -------
        pandas.DataFrame or object
            If `return_df` is True and the query result is not None, returns a 
            pandas DataFrame with the query results. The column names are derived 
            from the SELECT clause of the query. If `return_df` is False or the 
            query result is None, returns the raw query result.

        Notes
        -----
        - The method assumes that the query string contains a SELECT DISTINCT 
          clause if `return_df` is True.
        - The column names in the DataFrame are extracted from the SELECT clause 
          by removing the leading '?' from variable names.
        """
        res = kg.query(query_string)
        if res is not None:
            if return_df:
                for line in query_string.split("\n"):
                    if "SELECT DISTINCT" in line:
                        break
                labels = [x[1:] for x in line.split()[2:]]
                return pd.DataFrame(res, columns=labels)

        return res


class OntologyNetworkBase(Network):
    """
    Network representation of Onto
    """

    def __init__(self, onto):
        self.onto = onto
        self._terms = None
        self._g = None

    @property
    def terms(self):
        if self._terms is None:
            self._terms = AttrSetter()
            self._terms._add_attribute(self.onto.get_attributes())
        return self._terms

    @property
    def g(self):
        if self._g is None:
            self._g = self.onto.get_networkx_graph()
        return self._g

    def __add__(self, ontonetwork):
        onto = self.onto + ontonetwork.onto
        return OntologyNetworkBase(onto)

    @property
    def attributes(self):
        return self.onto.attributes

    @property
    def namespaces(self):
        return self.onto.namespaces

    @property
    def extra_namespaces(self):
        return self.onto.extra_namespaces

    def __radd__(self, ontonetwork):
        return self.__add__(ontonetwork)

    def add_namespace(self, namespace_name, namespace_iri):
        self.onto.add_namespace(namespace_name, namespace_iri)

    add_namespace.__doc__ = OntoParser.add_namespace.__doc__

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
        self.onto.add_term(
            uri=uri,
            node_type=node_type,
            namespace=namespace,
            dm=dm,
            rn=rn,
            data_type=data_type,
            node_id=node_id,
            delimiter=delimiter,
        )
        self._terms = None
        self._g = None

    add_term.__doc__ = OntoParser.add_term.__doc__

    def add_path(self, triple):
        """
        Add a triple as path.

        Note that all attributes of the triple should already exist in the graph.
        The ontology itself is not modified. Only the graph representation of it is.
        The expected use is to bridge between two (or more) different ontologies.

        Parameters
        ----------
        triple : tuple
        A tuple representing the triple to be added. The tuple should contain three elements:
        subject, predicate, and object.

        Raises
        ------
        ValueError
        If the subject or object of the triple is not found in the attributes of the ontology.

        """

        def to_uri(tag, namespaces):
            if ":" in tag:
                prefix, term = tag.split(":")
                return URIRef(namespaces[prefix] + term)
            else:
                return Literal(tag)

        sub, pred, obj = [to_uri(t, self.namespaces) for t in triple]

        if (sub, RDF.type, OWL.Class) not in self.onto.graph:
            raise ValueError(
                f"{sub} not found in {list(self.onto.graph.subjects(RDF.type, OWL.Class))}"
            )

        if (
            isinstance(obj, URIRef)
            and (obj, RDF.type, OWL.Class) not in self.onto.graph
        ):
            raise ValueError(
                f"{obj} not found in {list(self.onto.graph.subjects(RDF.type, OWL.Class))}"
            )

        self.onto.graph.add((sub, pred, obj))
        self._terms = None
        self._g = None


class OntologyNetwork(OntologyNetworkBase):
    """
    A class to represent an ontology network by extending the OntologyNetworkBase.

    This class initializes an ontology network by parsing the given ontology file.

    Parameters
    ----------
    infile : str
        The path to the ontology file to be parsed.
    format : str, optional
        The format of the ontology file (default is "xml").
    terms : AttrSetter
        An object for managing attributes of the ontology terms.
    g : networkx.Graph
        The NetworkX graph representation of the ontology.
    namespaces : dict
        A dictionary of namespaces defined in the ontology.
    extra_namespaces : dict
        Additional namespaces that are not part of the core ontology.
    """
    def __init__(self, infile, format="xml"):
        super().__init__(parse_ontology(infile, format=format))
