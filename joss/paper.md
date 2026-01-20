---
title: 'tools4RDF: A python toolkit for working with RDF data'
tags:
  - Python
  - RDF
  - Ontology
  - Semantics
  - Knowledge graphs
authors:
  - name: Sarath Menon
    orcid: 0000-0002-6776-1213
    affiliation: "1, 2" # (Multiple affiliations must be quoted)
  - name: Abril Azócar Guzmán
    orcid: 0000-0001-7564-7990
    affiliation: 3
  - name: Osamu Waseda
    orcid: 0000-0002-1677-4057
    affiliation: 1
  - name: Stefan Sandfeld
    orcid: 0000-0001-9560-4728
    affiliation: 3
  - name: Tilmann Hickel
    orcid: 0000-0003-0698-4891
    affiliation: 4
affiliations:
 - name: Max Planck Institute for Sustainable Materials, 40237 Düsseldorf, Germany
   index: 1
   ror: 01ngpvg12
 - name: ICAMS, Ruhr University Bochum, 44780 Bochum, Germany
   index: 2
   ror: 04tsk2644
 - name: Institute for Advanced Simulations – Materials Data Science and Informatics (IAS‑9), Forschungszentrum Jülich GmbH, 52425 Jülich, Germany
   index: 3
   ror: 02nv7yv05
 - name: Bundesanstalt für Materialforschung und -prüfung, 12489 Berlin, Germany
   index: 4
   ror: 03x516a66

date: 20 November 2025
bibliography: paper.bib
---

# Summary

tools4RDF is a lightweight Python framework designed to simplify working with RDF-based ontologies and data models. It allows one or more ontologies to be parsed and represented as Python classes, making it easier to navigate and explore their structure through features like autocompletion in interactive environments such as Jupyter notebooks. The framework preserves key semantic details such as domain and range information, which can then be used programmatically within Python workflows. A central goal of the tool is to make querying knowledge graphs with SPARQL more accessible to users without deep expertise in semantic web technologies. This is achieved through a programmatic interface that abstracts away much of the complexity involved in writing SPARQL queries. The overall workflow of the approach is illustrated in \autoref{fig:schematic}, showing how tools4RDF parses ontologies, constructs a network representation, and generates SPARQL queries to retrieve data from knowledge graphs. This design lowers the barrier to entry for domain scientists and developers unfamiliar with RDF, while still exposing enough control for advanced use cases. Originally developed for ontology-driven data integration in materials science, tools4RDF is ontology-agnostic and can be used across a wide range of scientific domains.

![Illustration of the working principle of tools4RDF. One or more ontologies are parsed using the tools4RDF parser and organized into a network representation. When the user specifies a source and destination, one or more connecting paths between these nodes are identified. Based on the selected pathway, a corresponding SPARQL query is generated, with optional constraints that can be applied. The knowledge graph is then queried, and the results are returned as a Pandas DataFrame.\label{fig:schematic}](schematic.jpg)

# Statement of need

Knowledge graphs [@gutierrez_knowledge_2020], coupled with formal ontologies, offer a promising technical approach for implementing the FAIR Guiding Principles [@wilkinson_fair_2016] for research data management. They support semantic interoperability, especially for aggregation and description of heterogeneous data [@vogt_suggestions_2025]. Accessing and querying these graphs typically relies on SPARQL [@w3c-sparql11], the standard query language for RDF data [@w3c-sparql11]. However, despite its potential, SPARQL remains difficult to use for many domain scientists due to unfamiliar syntax, steep learning curve, and the absence of a user-friendly tool stack [@Khamparia2017]. Libraries such as RDFLib [@Krech2025] offer core functionality for RDF parsing and graph storage but require users to write SPARQL queries and manipulate low-level graph objects. Tools like Protégé [@Musen2015] and SemTK [@Cuddihy2018] provide graphical interfaces for ontology exploration, but they focus on GUI-based interaction and lack integration with the Python ecosystem commonly used in scientific computing.

tools4RDF fills this gap by providing a Python-native interface for ontology exploration and query construction. By ingesting one or more ontologies and converting them into navigable Python classes, allowing users to navigate class hierarchies, properties, and relationships through autocompletion. This enables users to perform predicate-based graph traversal and generate SPARQL queries programmatically, without requiring manual SPARQL scripting. The framework tools4RDF supports a code-first workflow that allows domain scientists to explore semantic data in familiar environments such as Jupyter notebooks. Query results can be parsed directly into [Pandas](https://doi.org/10.5281/zenodo.3509134) [@mckinney-proc-scipy-2010] dataframes, facilitating integration with existing data processing pipelines. 

Beyond simplifying ontology interaction, this programmatic access to ontologies may also be useful for integrating semantic data into applications involving agentic AI or large language models (LLMs). Since tools4RDF guarantees the generation of structurally valid SPARQL queries that conform to the ontology schema, the task for the LLM is reduced to identifying source and destination terms, rather than constructing complete query syntax. This approach could eliminate common failure modes such as hallucinated entities [@Emonet2025], invalid property paths, and syntax errors [@Meyer2025], ensuring that every generated query is executable and semantically correct.

# Key features

## Parser for ontologies

tools4RDF includes a parser for ontologies that extracts classes, datatype properties, annotation properties, and hierarchical relationships such as subclasses and subproperties. It also parses and preserves domain and range definitions. The ontology is then represented as Python classes, which can be used programmatically in scripts and workflows to provide contextual knowledge.

Multiple ontologies can be parsed separately and their extraction can be  combined using the `+` operator. Links between classes from different ontologies can be defined in external files or added programmatically.

## Automated creation of SPARQL queries

Once the ontology terms are parsed, tools4RDF can generate SPARQL queries automatically if the source and destination terms are specified. Autocompletion helps users find relevant terms without needing detailed knowledge of the ontology. Internally, tools4RDF realises the ontology as a graph and traverses it to determine valid paths between terms. These paths are then converted to triples, which are then used in a SPARQL query.
    
Advanced features include: (i) restricting queries based on datatype properties, (ii) applying restrictions to queries using `<, >, <=, >=, ==` operators (iii) chaining restrictions and constructing complex queries using logical operators such as `&` and `|`, and (iv) manually specifying intermediate terms for fine-grained control. 
    
A simple SPARQL query, and the corresponding programmatic query creation. SPARQL code for querying a `Person`, and the corresponding `familyName` from DBpedia [@Auer2007] using the [FOAF](http://xmlns.com/foaf/spec/) ontology, and showing the first ten results is as follows:

```sparql
PREFIX foaf: <http://xmlns.com/foaf/0.1/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
SELECT DISTINCT ?Person ?familyNamevalue
WHERE {
    ?Person foaf:familyName ?familyNamevalue .
   { ?Person rdf:type foaf:Person . }
}
LIMIT 10
```

Corresponding code example demonstrating how tools4RDF can be used to construct the SPARQL query: 

```python
from tools4rdf import OntologyNetwork
onto = OntologyNetwork('http://xmlns.com/foaf/0.1/')
df = onto.query(
    kg = 'https://dbpedia.org/sparql',
    source = onto.terms.foaf.Person,
    destinations = onto.terms.foaf.familyName,
    limit=10,
)
```

An `OntologyNetwork` object is first created using a selected ontology. The `query` function takes four arguments: `kg` specifies the SPARQL endpoint (which may also be local), `source` and `destination` define the two endpoints connected by the query, and `limit` determines the number of records to return. The query results are returned as a Pandas `DataFrame`.

tools4RDF employs a graph-based approach internally to ensure generated queries are ontologically valid. When a user specifies source and destination terms, the tool constructs a NetworkX [@Hagberg2008] graph representation of the ontology and computes the paths between the specified nodes. This ensures that only valid connections through the ontology structure are used. When multiple valid paths exist, the paths are ordered by increasing length. The user can retrieve the required number of paths or manually specify intermediate terms to select a specific path. The generated queries preserve domain and range constraints from the ontology, and type assertions are automatically included to ensure RDF-compliant results. Additionally, filter operations are validated against datatypes.

More examples, including the demonstration of the use of comparison and logical operators are available in the [documentation](https://tools4rdf.readthedocs.io/en/latest/docs/examples.html).

## Ontology visualization

tools4RDF also includes a simple ontology visualisation tool. It uses Graphviz [@gansner2000open] to generate quick visual representations of ontologies within Jupyter notebooks.
        
# Current limitations

## Translation of SPARQL functionality to Python

tools4RDF currently supports a [subset of SPARQL operations designed to cover common query patterns](https://tools4rdf.readthedocs.io/en/latest/#supported-sparql-keywords), making it accessible to users without prior experience in semantic web technologies. Advanced query features are not yet supported. However, expert users can generate an initial query with tools4RDF and then extend or refine it manually, and execute it. We expect the user community to engage with the tool and contribute toward extending SPARQL support.

## Reasoning

The queries generated by tools4RDF are based only on the information explicitly present in the input RDF-based files. No description logic reasoning is performed, so implicit relationships are not taken into account. This limitation could be addressed by combining tools4RDF with reasoning tools such as HermiT [@Glimm2014] as a preprocessing step to materialize inferences prior to query construction.

# Additional details

tools4RDF is available under MIT license from the repository: [github.com/OCDO/tools4RDF](https:/github.com/OCDO/tools4RDF).
The documentation, which includes installation instructions and examples, is available in the [webpage](https://tools4rdf.readthedocs.io/en/latest/).

# Acknowledgements

This work is part of/supported by the consortium NFDI-MatWerk, funded by the Deutsche Forschungsgemeinschaft (DFG, German Research Foundation) under the National Research Data Infrastructure – NFDI 38/1 – project number 460247524.

# References
