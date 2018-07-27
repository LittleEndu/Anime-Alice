def merge(a, b, path=None):
    "merges b into a"
    if path is None: path = []
    for key in b:
        if key in a:
            if isinstance(a[key], dict) and isinstance(b[key], dict):
                merge(a[key], b[key], path + [str(key)])
            elif a[key] == b[key]:
                pass  # same leaf value
            else:
                raise Exception('Conflict at %s' % '.'.join(path + [str(key)]))
        else:
            a[key] = b[key]
    return a


class GraphQLKey:
    def __init__(self, *, name, signature=None, keys: tuple = None):
        self.name = name
        self.signature = signature or ""
        if keys:
            for key in keys:
                if not isinstance(key, GraphQLKey):
                    raise TypeError
        self.keys = keys or tuple()

    def __eq__(self, other):
        if isinstance(other, GraphQLKey):
            print(f"{self} {'==' if str(self)==str(other) else '!='} {other}")
            return str(self) == str(other)
        if isinstance(other, str):
            return self.name == other
        return NotImplemented

    def __getitem__(self, item) -> 'GraphQLKey':
        if isinstance(item, str):
            for key in self.keys:
                if key.name == item:
                    return key
            new_key = GraphQLKey(name=item)
            self.keys += (new_key,)
            return new_key
        elif isinstance(item, GraphQLKey):
            for key in self.keys:
                if key.name == item.name:
                    return key
            self.keys += (item,)
            return item
        raise TypeError

    def __str__(self):
        after = ""
        if self.signature:
            after += f"({self.signature})"
        if self.keys:
            after += "{" + " ".join(map(str, self.keys)) + "}"
        return f"{self.name}{after}"

    def __add__(self, other):
        if isinstance(other, dict):
            other = GraphQLKey.from_dict(other, name=self.name)
        if not isinstance(other, GraphQLKey):
            raise TypeError(f"unsupported operand type(s) for +=: 'GraphQLKey' and '{type(other)}'")
        if not self.name == other.name:
            raise ValueError('names must equal')
        return GraphQLKey.from_dict(merge(self.to_dict(), other.to_dict()))

    def __sub__(self, other):
        if isinstance(other, dict):
            other = GraphQLKey.from_dict(other, name=self.name)
        if not isinstance(other, GraphQLKey):
            raise TypeError(f"unsupported operand type(s) for -: 'GraphQLKey' and '{type(other)}'")
        if not self.name == other.name:
            raise ValueError('names must equal')
        for key in other.keys:
            my_keys = tuple()
            for i in self.keys:
                if i.name == key.name and len(i.keys) > 0 and len(key.keys) > 0:
                    my_keys += (i - key,)
                elif key != i:
                    my_keys += (i,)
            self.keys = my_keys
        return self

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
            if isinstance(dictionary[key], list):
                dictionary[key] = dictionary[key][0]
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


dd = {'Media': ('id: $id, type: ANIME', {'id': '_', 'siteUrl': '_', 'description': '_', 'episodes': '_',
                                         'title': {'romaji': '_', 'english': '_', 'native': '_'}, 'status': '_',
                                         'stats': {'scoreDistribution': {'score': '_', 'amount': '_'}},
                                         'startDate': {'year': '_', 'month': '_', 'day': '_'},
                                         'endDate': {'year': '_', 'month': '_', 'day': '_'},
                                         'coverImage': {'large': '_'}})}
dd2 = {'Media': {'id': '_', 'isAdult': '_', 'title': {'romaji': '_', 'english': '_'}, 'popularity': '_'}}
graph = GraphQLKey.from_dict(dd)
graph2 = GraphQLKey.from_dict(dd2)
graph -= graph2
print(graph)
