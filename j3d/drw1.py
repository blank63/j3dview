from enum import Enum
from btypes.big_endian import *


class Header(Struct):
    magic = ByteString(4)
    section_size = uint32
    matrix_definition_count = uint16
    __padding__ = Padding(2)
    matrix_type_offset = uint32
    index_offset = uint32

    def __init__(self):
        self.magic = b'DRW1'

    @classmethod
    def unpack(cls, stream):
        header = super().unpack(stream)
        if header.magic != b'DRW1':
            raise FormatError(f'invalid magic: {header.magic}')
        return header


class MatrixType(Enum):
    JOINT = 0
    INFLUENCE_GROUP = 1


class MatrixDefinition:

    def __init__(self, matrix_type, index):
        self.matrix_type = matrix_type
        self.index = index


def pack(stream, matrix_definitions):
    base = stream.tell()
    header = Header()
    header.matrix_definition_count = len(matrix_definitions)
    stream.write(b'\x00'*Header.sizeof())

    header.matrix_type_offset = stream.tell() - base
    for matrix_definition in matrix_definitions:
        uint8.pack(stream, matrix_definition.matrix_type.value)

    align(stream, 2)
    header.index_offset = stream.tell() - base
    for matrix_definition in matrix_definitions:
        uint16.pack(stream, matrix_definition.index)

    align(stream, 0x20)
    header.section_size = stream.tell() - base
    stream.seek(base)
    Header.pack(stream, header)
    stream.seek(base + header.section_size)


def unpack(stream):
    base = stream.tell()
    header = Header.unpack(stream)

    matrix_definitions = [
        MatrixDefinition(None, None)
        for _ in range(header.matrix_definition_count)
    ]

    stream.seek(base + header.matrix_type_offset)
    for matrix_definition in matrix_definitions:
        matrix_definition.matrix_type = MatrixType(uint8.unpack(stream))

    stream.seek(base + header.index_offset)
    for matrix_definition in matrix_definitions:
        matrix_definition.index = uint16.unpack(stream)

    stream.seek(base + header.section_size)
    return matrix_definitions

