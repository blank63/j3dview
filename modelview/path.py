import re


ATTRIBUTE_FRAGMENT_PATTERN = r'\.[A-Za-z_][A-Za-z0-9_]*'
ITEM_FRAGMENT_PATTERN = r'\[\d+\]'
FRAGMENT_PATTERN = '|'.join((
    f'(?P<attribute>{ATTRIBUTE_FRAGMENT_PATTERN})',
    f'(?P<item>{ITEM_FRAGMENT_PATTERN})'
))
FRAGMENT_PATTERN = re.compile(FRAGMENT_PATTERN)


class AttributePathFragment:

    __slots__ = ['name']

    def __init__(self, name):
        super().__setattr__('name', name)

    def __setattr__(self, name, value):
        raise AttributeError(f'Cannot assign to field {name}')

    def __delattr__(self, name):
        raise AttributeError(f'Cannot delete field {name}')

    def __eq__(self, other):
        if not isinstance(other, AttributePathFragment):
            return False
        return self.name == other.name

    def __hash__(self):
        return hash(self.name)

    def __str__(self):
        return f'.{self.name}'

    def match(self, other):
        return self == other

    def get_value(self, obj):
        return getattr(obj, self.name)

    def set_value(self, obj, value):
        setattr(obj, self.name, value)


class ItemPathFragment:

    __slots__ = ['key']

    def __init__(self, key):
        super().__setattr__('key', key)

    def __setattr__(self, name, value):
        raise AttributeError(f'Cannot assign to field {name}')

    def __delattr__(self, name):
        raise AttributeError(f'Cannot delete field {name}')

    def __eq__(self, other):
        if not isinstance(other, ItemPathFragment):
            return False
        return self.key == other.key

    def __hash__(self):
        return hash(self.key)

    def __str__(self):
        return f'[{self.key}]'

    def match(self, other):
        if not isinstance(other, ItemPathFragment):
            return False
        if self.key is ... or other.key is ...:
            return True
        return self.key == other.key

    def get_value(self, obj):
        return obj[self.key]

    def set_value(self, obj, value):
        obj[self.key] = value


class Path(tuple):

    def __getitem__(self, key):
        if isinstance(key, slice):
            return Path(super().__getitem__(key))
        return super().__getitem__(key)

    def __add__(self, other):
        if not isinstance(other, Path):
            return NotImplemented
        return Path(super().__add__(other))

    def __str__(self):
        return ''.join(str(fragment) for fragment in self)

    def match(self, other):
        if len(self) != len(other):
            return False
        return all(a.match(b) for a, b in zip(self, other))

    def get_value(self, obj):
        for fragment in self:
            obj = fragment.get_value(obj)
        return obj

    def set_value(self, obj, value):
        for i in range(len(self) - 1):
            obj = self[i].get_value(obj)
        self[-1].set_value(obj, value)

    @staticmethod
    def for_attribute(name):
        return Path((AttributePathFragment(name),))

    @staticmethod
    def for_item(key):
        return Path((ItemPathFragment(key),))

    @staticmethod
    def from_string(string):
        fragments = []
        position = 0
        while position < len(string):
            match = FRAGMENT_PATTERN.match(string, position)
            if match is None:
                raise ValueError('Invalid path string')
            if match['attribute'] is not None:
                name = match['attribute'].lstrip('.')
                fragment = AttributePathFragment(name)
            elif match['item'] is not None:
                key = int(match['item'].strip('[]'))
                fragment = ItemPathFragment(key)
            else:
                assert False
            fragments.append(fragment)
            position = match.end()
        return Path(fragments)


class PathBuilder:

    def __init__(self, path=Path()):
        self.__path = path

    def __getattr__(self, name):
        return PathBuilder(self.__path + Path.for_attribute(name))

    def __getitem__(self, key):
        return PathBuilder(self.__path + Path.for_item(key))

    def __pos__(self):
        """Return the built path.

        Using the unary plus operator for this is admittedly somewhat jank, but
        it allows for path building to be expressed very succinctly.
        """
        return self.__path

    def __radd__(self, other):
        if isinstance(other, Path):
            return other + self.__path
        return NotImplemented


PATH_BUILDER = PathBuilder()

