import numpy
from btypes.big_endian import *


class Header(Struct):
    magic = ByteString(4)
    section_size = uint32
    influence_group_count = uint16
    __padding__ = Padding(2)
    influence_count_offset = uint32
    index_offset = uint32
    weight_offset = uint32
    inverse_bind_matrix_offset = uint32

    def __init__(self):
        self.magic = b'EVP1'

    @classmethod
    def unpack(cls, stream):
        header = super().unpack(stream)
        if header.magic != b'EVP1':
            raise FormatError('invalid magic')
        return header


class Influence:

    def __init__(self, index, weight):
        self.index = index
        self.weight = weight


def pack(stream, influence_groups, inverse_bind_matrices):
    base = stream.tell()
    header = Header()
    header.influence_group_count = len(influence_groups)
    header.influence_count_offset = 0
    header.index_offset = 0
    header.weight_offset = 0
    header.inverse_bind_matrix_offset = 0
    stream.write(b'\x00'*Header.sizeof())

    if influence_groups:
        header.influence_count_offset = stream.tell() - base
        for influence_group in influence_groups:
            uint8.pack(stream, len(influence_group))

        header.index_offset = stream.tell() - base
        for influence_group in influence_groups:
            for influence in influence_group:
                uint16.pack(stream, influence.index)

        align(stream, 4)
        header.weight_offset = stream.tell() - base
        for influence_group in influence_groups:
            for influence in influence_group:
                float32.pack(stream, influence.weight)

    if inverse_bind_matrices is not None:
        header.inverse_bind_matrix_offset = stream.tell() - base
        inverse_bind_matrices.tofile(stream)

    align(stream, 0x20)
    header.section_size = stream.tell() - base
    stream.seek(base)
    Header.pack(stream, header)
    stream.seek(base + header.section_size)


def unpack(stream):
    base = stream.tell()
    header = Header.unpack(stream)

    influence_groups = [None]*header.influence_group_count
    inverse_bind_matrices = None

    stream.seek(base + header.influence_count_offset)
    for i in range(header.influence_group_count):
        influence_count = uint8.unpack(stream)
        influence_groups[i] = [Influence(None, None) for _ in range(influence_count)]

    stream.seek(base + header.index_offset)
    for influence_group in influence_groups:
        for influence in influence_group:
            influence.index = uint16.unpack(stream)

    stream.seek(base + header.weight_offset)
    for influence_group in influence_groups:
        for influence in influence_group:
            influence.weight = float32.unpack(stream)

    if header.inverse_bind_matrix_offset != 0:
        stream.seek(base + header.inverse_bind_matrix_offset)
        element_type = numpy.dtype((numpy.float32, (3, 4))).newbyteorder('>')
        element_count = (header.section_size - header.inverse_bind_matrix_offset)//element_type.itemsize
        inverse_bind_matrices = numpy.fromfile(stream, element_type, element_count)

    stream.seek(base + header.section_size)
    return influence_groups, inverse_bind_matrices

