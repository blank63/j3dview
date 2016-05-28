from collections import OrderedDict


class Haystack:

    def __init__(self):
        self.keys = []
        self.values = []

    def __contains__(self,key):
        return key in self.keys

    def __missing__(self,key):
        raise KeyError(key)

    def __getitem__(self,key):
        try:
            return self.values[self.keys.index(key)]
        except ValueError:
            return self.__missing__(key)

    def __setitem__(self,key,value):
        try:
            self.values[self.keys.index(key)] = value
        except ValueError:
            self.keys.append(key)
            self.values.append(value)

    def __iter__(self):
        yield from self.keys


class OffsetPoolPacker:

    def __init__(self,stream,pack_function,base=0,default_offset_table=None):
        self.stream = stream
        self.pack_function = pack_function
        self.base = base
        self.offset_table = default_offset_table if default_offset_table is not None else {}

    def __call__(self,*args):
        if args in self.offset_table:
            return self.offset_table[args]

        offset = self.stream.tell() - self.base
        self.pack_function(self.stream,*args)
        self.offset_table[args] = offset
        return offset


class OffsetPoolUnpacker:

    def __init__(self,stream,unpack_function,base=0):
        self.stream = stream
        self.unpack_function = unpack_function
        self.base = base
        self.argument_table = {}
        self.value_table = {}

    def __call__(self,offset,*args):
        if offset in self.value_table:
            if args != self.argument_table[offset]:
                raise ValueError('inconsistent arguments for same offset')
            return self.value_table[offset]

        self.stream.seek(self.base + offset)
        value = self.unpack_function(self.stream,*args)
        self.argument_table[offset] = args
        self.value_table[offset] = value
        return value

