import yaml
import os
import numpy as np

doc_fields = ["doc", "url"]


def read_yaml(filename):
    with open(filename, "r") as fin:
        data = yaml.safe_load(fin)
        return data


def _get_doc_from_key(keydict):
    url = keydict["url"] if "url" in keydict.keys() else None

    doc = f"""
    {keydict["doc"]}
    url: {url}
    """
    return doc


class MyList(list):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class AttrSetter:
    """
    Class which enables tab completed, contextual attributes
    """

    def __init__(self):
        self._map_dict = {}
        self.head = None

    def __dir__(self):
        """
        Gives tab completion
        """
        return list(self._map_dict.keys())

    def __repr__(self):
        """
        String representation
        """
        return ", ".join(list(self._map_dict.keys()))

    def __getattr__(self, key):
        """
        Calls attributes from the class when general lookup fails. There are four main types of
        calls that can occur.

        Normal attribute: this function does not get called
        key which is present in `_map_dict`: filter and call it
        key which add ons: for example `position_selected` or `position_not_selected`
        key does not exist: raise `AttributeError`
        """
        if key in self._map_dict.keys():
            if self.head is None:
                self.head = self
            return self._map_dict[key]

        else:
            raise AttributeError(f"Attribute {key} not found")

    def _add_attribute(self, indict, head=None):
        if head is None:
            head = self
        self.head = head

        for key, val in indict.items():
            if isinstance(val, dict):
                if key not in self._map_dict.keys():
                    self._map_dict[key] = AttrSetter()

                self._map_dict[key]._add_attribute(val, head=head)
            else:
                self._map_dict[key] = val
