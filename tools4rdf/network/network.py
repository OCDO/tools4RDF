import networkx as nx
import graphviz
import pandas as pd

from tools4rdf.network.attrsetter import AttrSetter
from tools4rdf.network.parser import parse_ontology, OntoParser


def _replace_name(name):
    return ".".join(name.split(":"))


class OntologyNetworkBase:
    """
    Network representation of Onto
    """

    def __init__(self, onto):
        self.onto = onto
        self.terms = AttrSetter()
        self.g = self.onto.get_networkx_graph()
        self._assign_attributes()

    def _assign_attributes(self):
        self.terms._add_attribute(self.onto.get_attributes())

    def __add__(self, ontonetwork):
        onto = self.onto + ontonetwork.onto
        return OntologyNetworkBase(onto)

    def strip_name(self, name):
        raw = name.split(":")
        if len(raw) > 1:
            return raw[-1]
        return name

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
        self._assign_attributes()

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
        sub = triple[0]
        pred = triple[1]
        obj = triple[2]

        if sub not in self.onto.attributes["class"].keys():
            raise ValueError(f"{sub} not found in self.attributes")

        # now add
        self.g.add_edge(sub, pred)
        for subclass in self.onto.attributes["class"][sub].subclasses:
            self.g.add_edge(subclass, pred)

        # now add pred
        if pred in self.onto.attributes["object_property"].keys():
            if obj not in self.onto.attributes["class"].keys():
                raise ValueError(f"{obj} not found in self.attributes")
            # subclasses = self.onto._get_subclasses(obj)
            self.g.add_edge(pred, obj)
            for subclass in self.onto.attributes["class"][obj].subclasses:
                self.g.add_edge(pred, subclass)

        # another possibility it is data property
        elif pred in self.onto.attributes["data_property"].keys():
            data_node = f"{pred}value"
            self.g.add_node(data_node, node_type="literal", data_type=obj)
            self.g.add_edge(pred, data_node)

        else:
            raise ValueError(f"{pred} not found in self.attributes")

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

    def _get_shortest_path(self, source, target):
        # this function will be modified to take OntoTerms direcl as input; and use their names.
        path = nx.shortest_path(
            self.g, source=source.query_name, target=target.query_name
        )
        # replace the start and end with thier corresponding variable names
        path[0] = source.variable_name
        path[-1] = target.variable_name
        return path

    def get_shortest_path(self, source, target, triples=False):
        """
        Compute the shortest path between two nodes in the graph.

        Parameters:
        -----------
        source : node
            The starting node for the path.
        target : node
            The target node for the path.
        triples : bool, optional
            If True, returns the path as a list of triples. Each triple consists
            of three consecutive nodes in the path. If False, returns the path
            as a list of nodes.

        Returns:
        --------
        path : list
            The shortest path between the source and target nodes. If `triples`
            is True, the path is returned as a list of triples. If `triples` is
            False, the path is returned as a list of nodes.

        """
        # this function should also check for stepped queries
        path = []
        if len(target._parents) > 0:
            # this needs a stepped query
            complete_list = [source, *target._parents, target]
            # get path for first two terms
            path = self._get_shortest_path(complete_list[0], complete_list[1])
            for x in range(2, len(complete_list)):
                temp_source = complete_list[x - 1]
                temp_dest = complete_list[x]
                temp_path = self._get_shortest_path(temp_source, temp_dest)
                path.extend(temp_path[1:])
        else:
            path = self._get_shortest_path(source, target)

        if triples:
            triple_list = []
            for x in range(len(path) // 2):
                triple_list.append(path[2 * x: 2 * x + 3])
            return triple_list

        return path

    def create_query(self, source, destinations, enforce_types=True):
        """
        Create a SPARQL query string based on the given source, destinations, condition, and enforce_types.

        Parameters
        ----------
        source : Node
            The source node from which the query starts.
        destinations : list or Node
            The destination node(s) to which the query should reach. If a single
            node is provided, it will be converted to a list.
        enforce_types : bool, optional
            Whether to enforce the types of the source and destination nodes in the query. Defaults to True.

        Returns
        -------
        str
            The generated SPARQL query string.

        """
        # if not list, convert to list
        if not isinstance(destinations, list):
            destinations = [destinations]

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

        # all names are now collected, in a list of lists
        # start prefix of query
        query = []
        for key, val in self.namespaces.items():
            query.append(f"PREFIX {key}: <{val}>")
        for key, val in self.extra_namespaces.items():
            query.append(f"PREFIX {key}: <{val}>")

        # construct the select distinct command:
        # add source `variable_name`
        # iterate over destinations, add their `variable_name`
        select_destinations = [
            "?" + destination.variable_name for destination in destinations
        ]
        select_destinations = ["?" + source.variable_name] + select_destinations
        query.append(f'SELECT DISTINCT {" ".join(select_destinations)}')
        query.append("WHERE {")

        # constructing the spaql query path triples, by iterating over destinations
        # for each destination:
        #    - check if it has  parent by looking at `._parents`
        #    - if it has `_parents`, called step path method
        #    - else just get the path
        #    - replace the ends of the path with `variable_name`
        #    - if it deosnt exist in the collection of lines, add the lines
        for count, destination in enumerate(destinations):
            # print(source, destination)
            triplets = self.get_shortest_path(source, destination, triples=True)
            # print(triplets)
            for triple in triplets:
                # print(triple)
                line_text = "    ?%s %s ?%s ." % (
                    triple[0].replace(":", "_"),
                    triple[1],
                    triple[2].replace(":", "_"),
                )
                if line_text not in query:
                    query.append(line_text)

        # we enforce types of the source and destination
        if enforce_types:
            if source.node_type == "class":
                query.append(
                    "    ?%s rdf:type %s ."
                    % (self.strip_name(source.variable_name), source.query_name)
                )

            for destination in destinations:
                if destination.node_type == "class":
                    query.append(
                        "    ?%s rdf:type %s ."
                        % (
                            destination.variable_name,
                            destination.query_name,
                        )
                    )
        # - formulate the condition, given by the `FILTER` command:
        #    - extract the filter text from the term
        #    - loop over destinations:
        #        - call `replace(destination.query_name, destination.variable_name)`
        filter_text = ""

        # make filters; get all the unique filters from all the classes in destinations
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

        return "\n".join(query)

    def query(self, kg, source, destinations, enforce_types=True, return_df=True):
        query_string = self.create_query(
            source, destinations, enforce_types=enforce_types
        )
        res = kg.query(query_string)
        if res is not None:
            if return_df:
                for line in query_string.split("\n"):
                    if "SELECT DISTINCT" in line:
                        break
                labels = [x[1:] for x in line.split()[2:]]
                return pd.DataFrame(res, columns=labels)

        return res


class OntologyNetwork(OntologyNetworkBase):
    """
    Network representation of Onto
    """

    def __init__(self, infile):
        super().__init__(parse_ontology(infile))
