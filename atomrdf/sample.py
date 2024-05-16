"""
Sample

In this module a new Sample class is defined.
"""
from pyscal3.atoms import AttrSetter
from atomrdf.namespace import CMSO, PLDO, PODO, ASMO, PROV
from rdflib import RDFS, Namespace, RDF, URIRef, Literal
import numpy as np
import uuid

MATH = Namespace("http://purls.helmholtz-metadaten.de/asmo/")

class Sample:
    def __init__(self, name, sample_id, graph):
        self._name = name
        self._sample_id = sample_id
        self._graph = graph

        #create attributes
        self.properties = AttrSetter()
        mapdict = {
            'volume': self._volume,
            'no_of_atoms': self._no_of_atoms,
        }
        self.properties._add_attribute(mapdict)

        labels, props = self._input_properties
        self.inputs = AttrSetter()
        mapdict = {}
        for key, value in zip(labels, props):
            if key is not None:
                mapdict[key] = value
        self.inputs._add_attribute(mapdict)

        labels, props = self._output_properties
        self.outputs = AttrSetter()
        mapdict = {}
        for key, value in zip(labels, props):
            if key is not None:
                mapdict[key] = value
        self.outputs._add_attribute(mapdict)

    def __str__(self):
        return f"{self._name}"
    
    def __repr__(self):
        return f"{self._name}"
    
    @property
    def _volume(self):
        simcell = self._graph.value(self._sample_id, CMSO.hasSimulationCell)
        volume = self._graph.value(simcell, CMSO.hasVolume)
        return Property(volume.toPython(), graph=self._graph)
    
    @property
    def _no_of_atoms(self):
        no_atoms = self._graph.value(self._sample_id, CMSO.hasNumberOfAtoms)
        return Property(no_atoms.toPython(), graph=self._graph)
    
    @property
    def _input_properties(self):
        activity = self._graph.value(self._sample_id, PROV.wasGeneratedBy)
        if activity is not None:
            inps = [k[2] for k in self._graph.triples((activity, ASMO.hasInputParameter, None))]
            labels = [self._graph.value(inp, RDFS.label) for inp in inps]
            labels = [label if label is None else label.toPython() for label in labels]
            values = [self._graph.value(inp, ASMO.hasValue) for inp in inps]
            units = [self._graph.value(inp, ASMO.hasUnit) for inp in inps]
            units = [unit if unit is None else unit.toPython().split('/')[-1] for unit in units]
            props = []
            for count, value in enumerate(values):
                props.append(Property(value.toPython(), unit=units[count], graph=self._graph, parent=inps[count]))
            return labels, props
        return [], []
    
    @property
    def _output_properties(self):
        inps = [k[2] for k in self._graph.triples((self._sample_id, CMSO.hasCalculatedProperty, None))]
        labels = [self._graph.value(inp, RDFS.label) for inp in inps]
        labels = [label if label is None else label.toPython() for label in labels]
        values = [self._graph.value(inp, ASMO.hasValue) for inp in inps]
        units = [self._graph.value(inp, ASMO.hasUnit) for inp in inps]
        units = [unit if unit is None else unit.toPython().split('/')[-1] for unit in units]
        props = []
        for count, value in enumerate(values):
            props.append(Property(value.toPython(), unit=units[count], graph=self._graph, parent=inps[count]))
        return labels, props

class Property:
    def __init__(self, value, unit=None, graph=None, parent=None):
        self._value = value
        self._unit = unit
        self._graph = graph
        self._parent = parent
    
    def __repr__(self):
        if self._unit is not None:
            return f"{self._value} {self._unit}"
        return f"{self._value}"
    
    @property
    def value(self):
        return self._value
    
    def _declass(self, item):
        if isinstance(item, Property):
            return item.value
        else:
            return item

    def _wrap(self, value):
        if isinstance(value, Property):
            return value._parent
        else:
            return Literal(value)

    #overloaded operations
    def __add__(self, value):
        res = self._value + self._declass(value)
        res_prop = Property(res, unit=self._unit, graph=self._graph, parent=self._parent) 
        if self._graph is not None:
            operation = URIRef(f'operation:{uuid.uuid4()}')
            self._graph.add((operation, RDF.type, MATH.Addition))
            self._graph.add((operation, MATH.hasAddend, self._wrap(self)))
            self._graph.add((operation, MATH.hasSum, self._wrap(res_prop)))
        return res_prop
    
    def __sub__(self, value):
        return Property(self._value - self._declass(value), unit=self._unit, graph=self._graph, parent=self._parent)
    
    def __mul__(self, value):
        return Property(self._value * self._declass(value), unit=self._unit, graph=self._graph, parent=self._parent)

    def __truediv__(self, value):
        return Property(self._value / self._declass(value), unit=self._unit, graph=self._graph, parent=self._parent)
    
    def __eq__(self, value):
        return self._value == self._declass(value)

    def __ne__(self, value):
        return self._value != self._declass(value)
    
    def __lt__(self, value):
        return self._value < self._declass(value)
    
    def __le__(self, value):
        return self._value <= self._declass(value)
    
    def __gt__(self, value):
        return self._value > self._declass(value)
    
    def __ge__(self, value):
        return self._value >= self._declass(value)
    
    def __neg__(self):
        return Property(-self._value, unit=self._unit, graph=self._graph, parent=self._parent)
    
    def __abs__(self):
        return Property(abs(self._value), unit=self._unit, graph=self._graph, parent=self._parent)
    
    def __round__(self, n):
        return Property(round(self._value, n), unit=self._unit, graph=self._graph, parent=self._parent)