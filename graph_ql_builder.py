import pyperclip

class GraphQLKey:
    def __init__(self, *, name, signature=None, keys: list = None):
        self.name = name
        self.signature = signature or ""
        if keys:
            for key in keys:
                if not isinstance(key, GraphQLKey):
                    raise TypeError
        self.keys = keys or list()

    def __eq__(self, other):
        if isinstance(other, GraphQLKey):
            return self.name == other.name
        if isinstance(other, str):
            return self.name == other
        raise NotImplemented

    def __getitem__(self, item) -> 'GraphQLKey':
        if isinstance(item, str):
            for key in self.keys:
                if key.name == item:
                    return key
            new_key = GraphQLKey(name=item)
            self.keys.append(new_key)
            return new_key
        elif isinstance(item, GraphQLKey):
            for key in self.keys:
                if key.name == item.name:
                    return key
            self.keys.append(item)
            return item
        raise TypeError

    def __str__(self):
        after = ""
        if self.signature:
            after += f"({self.signature})"
        if self.keys:
            after += "{" + " ".join(map(str, self.keys)) + "}"
        return f"{self.name}{after}"

    def __iadd__(self, other):
        if isinstance(other, dict):
            other = GraphQLKey.from_dict(other, name=self.name)
        if not isinstance(other, GraphQLKey):
            return TypeError(f"unsupported operand type(s) for +=: 'GraphQLKey' and '{type(other)}'")
        if not self.name == other.name:
            return ValueError('names must equal')
        for key in other.keys:
            if key not in self.keys:
                self.keys.append(key)

    def __isub__(self, other):
        if isinstance(other, dict):
            other = GraphQLKey.from_dict(other, name=self.name)
        if not isinstance(other, GraphQLKey):
            return TypeError(f"unsupported operand type(s) for -=: 'GraphQLKey' and '{type(other)}'")
        if not self.name == other.name:
            return ValueError('names must equal')
        for key in other.keys:
            if key in self.keys:
                self.keys.remove(key)

    @staticmethod
    def from_dict(dictionary: dict, *, name=None, signature=None):
        if name is None:
            if len(dictionary) > 1:
                raise ValueError('must provide name or have a dict with one key')
            name = list(dictionary.keys())[0]
            if not isinstance(name, str):
                raise TypeError('must provide name or key in dict must be str')
            if isinstance(dictionary[name], tuple):
                rv = GraphQLKey(name=name, signature=dictionary[name][0])
                dictionary = dictionary[name][1]
            else:
                rv = GraphQLKey(name=name)
                dictionary = dictionary[name]
        else:
            rv = GraphQLKey(name=name, signature=signature)
        for key in dictionary:
            assert isinstance(key, str)
            if isinstance(dictionary[key], dict):
                _ = rv[GraphQLKey.from_dict(dictionary[key], name=key)]
            elif isinstance(dictionary[key], tuple):
                _ = rv[GraphQLKey.from_dict(dictionary[key][1], name=key, signature=dictionary[key][0])]
            else:
                _ = rv[key]
        return rv

    def to_dict(self):
        rv = dict()
        if self.signature:
            dd = dict()
            for key_dict in [key.to_dict() for key in self.keys]:
                dd = {**dd, **key_dict}
            rv[self.name] = (self.signature, dd if dd else '_')
        else:
            dd = dict()
            for key_dict in [key.to_dict() for key in self.keys]:
                dd = {**dd, **key_dict}
            rv[self.name] = dd if dd else '_'
        return rv


dd = {'query': ('$id: Int',
                {'Character': ('id: $id',
                               {'description': '_',
                                'name':
                                    {'native': '_',
                                     'alternative': '_'},
                                'siteUrl': '_',
                                'image':
                                    {'large': '_'}
                                })
                 })
      }

query = GraphQLKey.from_dict(dd)
dd = query.to_dict()
query2 = GraphQLKey.from_dict(dd)
pyperclip.copy(str(query2))
print(dd)
