from enum import IntEnum
from btypes.big_endian import *


class Header(Struct):
    magic = ByteString(4)
    section_size = uint32
    matrix_descriptor_count = uint16
    __padding__ = Padding(2)
    matrix_type_offset = uint32
    index_offset = uint32

    def __init__(self):
        self.magic = b'DRW1'

    @classmethod
    def unpack(cls,stream):
        header = super().unpack(stream)
        if header.magic != b'DRW1':
            raise FormatError('invalid magic')
        return header


class MatrixType(IntEnum):
    JOINT = 0
    INFLUENCE_GROUP = 1


class MatrixDescriptor:

    def __init__(self,matrix_type,index):
        self.matrix_type = matrix_type
        self.index = index


def pack(stream,matrix_descriptors):
    base = stream.tell()
    header = Header()
    header.matrix_descriptor_count = len(matrix_descriptors)
    stream.write(b'\x00'*Header.sizeof())

    header.matrix_type_offset = stream.tell() - base
    for matrix_descriptor in matrix_descriptors:
        uint8.pack(stream,matrix_descriptor.matrix_type)

    align(stream,2)
    header.index_offset = stream.tell() - base
    for matrix_descriptor in matrix_descriptors:
        uint16.pack(stream,matrix_descriptor.index)

    align(stream,0x20)
    header.section_size = stream.tell() - base
    stream.seek(base)
    Header.pack(stream,header)
    stream.seek(base + header.section_size)


def unpack(stream):
    base = stream.tell()
    header = Header.unpack(stream)

    matrix_descriptors = [MatrixDescriptor(None,None) for _ in range(header.matrix_descriptor_count)]

    stream.seek(base + header.matrix_type_offset)
    for matrix_descriptor in matrix_descriptors:
        matrix_descriptor.matrix_type = MatrixType(uint8.unpack(stream))

    stream.seek(base + header.index_offset)
    for matrix_descriptor in matrix_descriptors:
        matrix_descriptor.index = uint16.unpack(stream)

    stream.seek(base + header.section_size)
    return matrix_descriptors

