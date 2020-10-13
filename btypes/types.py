import copy
from struct import Struct as _Struct


class BasicType:

    def __init__(self, format_string):
        self._struct = _Struct(format_string)

    def pack(self, stream, value):
        stream.write(self._struct.pack(value))

    def pack_into(self, buffer, offset, value):
        self._struct.pack_into(buffer, offset, value)

    def unpack(self, stream):
        return self._struct.unpack(stream.read(self.sizeof()))[0]

    def unpack_from(self, buffer, offset):
        return self._struct.unpack_from(buffer, offset)[0]

    def sizeof(self):
        return self._struct.size


class FixedPointConverter:

    def __init__(self, integer_type, scale):
        self.integer_type = integer_type
        self.scale = scale

    def pack(self, stream, value):
        self.integer_type.pack(stream, round(value/self.scale))

    def unpack(self, stream):
        return self.integer_type.unpack(stream)*self.scale

    def sizeof(self):
        return self.integer_type.sizeof()


class EnumConverter:

    def __init__(self, integer_type, enumeration):
        self.integer_type = integer_type
        self.enumeration = enumeration

    def pack(self, stream, member):
        self.integer_type.pack(stream, member.value)

    def unpack(self, stream):
        return self.enumeration(self.integer_type.unpack(stream))

    def sizeof(self):
        return self.integer_type.sizeof()


class NoneableConverter:
    
    def __init__(self, base_type, none_value):
        self.base_type = base_type
        self.none_value = none_value
        
    def pack(self, stream, value):
        self.base_type.pack(stream, value if value is not None else self.none_value)
        
    def unpack(self, stream):
        value = self.base_type.unpack(stream)
        return value if value != self.none_value else None
        
    def sizeof(self):
        return self.base_type.sizeof()
        
        
class ByteString:

    def __init__(self, length):
        self.length = length

    def pack(self, stream, string):
        if len(string) != self.length:
            raise ValueError('Invalid string length')
        stream.write(string)

    def unpack(self, stream):
        return stream.read(self.length)

    def sizeof(self):
        return self.length


class Array:

    def __init__(self, element_type, length):
        self.element_type = element_type
        self.length = length

    def pack(self, stream, array):
        if len(array) != self.length:
            raise ValueError(f'expected array of length {self.length}, got array of length {len(array)}')
        for value in array:
            self.element_type.pack(stream, value)

    def unpack(self, stream):
        return [self.element_type.unpack(stream) for _ in range(self.length)]

    def sizeof(self):
        return self.length*self.element_type.sizeof()


class CString:

    def __init__(self, encoding):
        self.encoding = encoding

    def pack(self, stream, string):
        stream.write((string + '\0').encode(self.encoding))

    def unpack(self, stream):
        #XXX: This might not work for all encodings
        null = '\0'.encode(self.encoding)
        string = b''
        while True:
            c = stream.read(len(null))
            if c == null: break
            string += c
        return string.decode(self.encoding)

    def sizeof(self):
        return None


class PString:

    def __init__(self, encoding):
        self.encoding = encoding

    def pack(self, stream, string):
        string = string.encode(self.encoding)
        stream.write(bytes(chr(len(string))))
        stream.write(string)

    def unpack(self, stream):
        length = ord(stream.read(1))
        return stream.read(length).decode(self.encoding)

    def sizeof(self):
        return None


class TerminatedList:

    @classmethod
    def terminator_predicate(cls, element):
        return element == cls.terminator_value

    @classmethod
    def pack(cls, stream, elements):
        for element in elements:
            cls.element_type.pack(stream, element)
        cls.element_type.pack(stream, cls.terminator_value)

    @classmethod
    def unpack(cls, stream):
        elements = []
        while True:
            element = cls.element_type.unpack(stream)
            if cls.terminator_predicate(element): break
            elements.append(element)
        return elements

    @staticmethod
    def sizeof():
        return None


class Field:

    def __init__(self, name, field_type):
        self.name = name
        self.field_type = field_type

    def pack(self, stream, struct):
        self.field_type.pack(stream, getattr(struct, self.name))

    def unpack(self, stream, struct):
        setattr(struct, self.name, self.field_type.unpack(stream))

    def sizeof(self):
        return self.field_type.sizeof()

    def equal(self, struct, other):
        return getattr(struct, self.name) == getattr(other, self.name)


class Padding:

    def __init__(self, length, padding=b'\xFF'):
        self.length = length
        self.padding = padding

    def pack(self, stream, struct):
        stream.write(self.padding*self.length)

    def unpack(self, stream, struct):
        stream.read(self.length)

    def sizeof(self):
        return self.length

    def equal(self, struct, other):
        return True


class StructClassDictionary(dict):

    def __init__(self):
        super().__init__()
        self.struct_fields = []

    def __setitem__(self, key, value):
        if not key[:2] == key[-2:] == '__' and not hasattr(value, '__get__'):
            self.struct_fields.append(Field(key, value))
        elif key == '__padding__':
            self.struct_fields.append(value)
        else:
            super().__setitem__(key, value)


class StructMetaClass(type):

    @classmethod
    def __prepare__(metacls, cls, bases, replace_fields=False):
        return StructClassDictionary()

    def __new__(metacls, cls, bases, classdict, replace_fields=False):
        struct_class = super().__new__(metacls, cls, bases, classdict)

        if not classdict.struct_fields:
            return struct_class

        if not hasattr(struct_class, 'struct_fields'):
            struct_fields = classdict.struct_fields
        elif replace_fields:
            struct_fields = copy.copy(struct_class.struct_fields)
            metacls.replace_fields(struct_fields, classdict.struct_fields)
        else:
            raise TypeError('Cannot add fields to struct')

        def __eq__(self, other):
            return all(field.equal(self, other) for field in struct_fields)

        struct_class.struct_fields = struct_fields
        struct_class.struct_size = metacls.calculate_struct_size(struct_fields)
        struct_class.__eq__ = __eq__
        return struct_class

    def __init__(self, cls, bases, classdict, replace_fields=False):
        super().__init__(cls, bases, classdict)

    @staticmethod
    def calculate_struct_size(struct_fields):
        if any(field.sizeof() is None for field in struct_fields):
            return None
        return sum(field.sizeof() for field in struct_fields)

    @staticmethod
    def replace_fields(fields, replacement_fields):
        for replacement_field in replacement_fields:
            for i, field in enumerate(fields):
                if hasattr(field, 'name') and field.name == replacement_field.name:
                    fields[i] = replacement_field


class Struct(metaclass=StructMetaClass):

    __slots__ = tuple()

    @classmethod
    def pack(cls, stream, struct):
        for field in cls.struct_fields:
            field.pack(stream, struct)

    @classmethod
    def unpack(cls, stream):
        struct = cls.__new__(cls)
        for field in cls.struct_fields:
            field.unpack(stream, struct)
        return struct

    @classmethod
    def sizeof(cls):
        return cls.struct_size

