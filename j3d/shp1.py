import numpy
from btypes.big_endian import *
from btypes.utils import Haystack, OffsetPoolPacker, OffsetPoolUnpacker
import gx

import logging
logger = logging.getLogger(__name__)


class Header(Struct):
    magic = ByteString(4)
    section_size = uint32
    shape_count = uint16
    __padding__ = Padding(2)
    shape_offset = uint32
    index_offset = uint32
    unknown0_offset = uint32
    attribute_descriptor_offset = uint32
    matrix_index_offset = uint32
    packet_offset = uint32
    matrix_selection_offset = uint32
    packet_location_offset = uint32

    def __init__(self):
        self.magic = b'SHP1'

    @classmethod
    def unpack(cls, stream):
        header = super().unpack(stream)
        if header.magic != b'SHP1':
            raise FormatError('invalid magic')
        if header.unknown0_offset != 0:
            logger.warning('unknown0_offset different from default')
        return header


class AttributeDescriptor(Struct):
    """Arguments to GXSetVtxDesc."""
    attribute = EnumConverter(uint32, gx.Attribute)
    input_type = EnumConverter(uint32, gx.InputType)

    def __init__(self, attribute, input_type):
        self.attribute = attribute
        self.input_type = input_type

    def field(self):
        if (self.attribute == gx.VA_PTNMTXIDX or self.attribute in gx.VA_TEXMTXIDX) and self.input_type == gx.DIRECT:
            return (self.attribute.name, numpy.uint8)
        if self.input_type == gx.INDEX8:
            return (self.attribute.name, numpy.uint8)
        if self.input_type == gx.INDEX16:
            return (self.attribute.name, numpy.uint16)

        raise ValueError('invalid attribute descriptor')


class AttributeDescriptorList(TerminatedList):
    element_type = AttributeDescriptor
    terminator_value = element_type(gx.VA_NULL, gx.NONE)

    @staticmethod
    def terminator_predicate(element):
        return element.attribute == gx.VA_NULL


class MatrixSelection(Struct):
    unknown0 = uint16 # position/normal matrix for texture matrices?
    count = uint16
    first = uint32


class PacketLocation(Struct):
    size = uint32
    offset = uint32


class Primitive:

    def __init__(self, primitive_type, vertices):
        self.primitive_type = primitive_type
        self.vertices = vertices


class Batch:

    def __init__(self, primitives, matrix_table, unknown0):
        self.primitives = primitives
        self.matrix_table = matrix_table
        self.unknown0 = unknown0

    
class Shape(Struct):
    transformation_type = uint8
    __padding__ = Padding(1)
    batch_count = uint16
    attribute_descriptor_offset = uint16
    first_matrix_selection = uint16
    first_packet = uint16
    __padding__ = Padding(2)
    bounding_radius = float32
    min_x = float32
    min_y = float32
    min_z = float32
    max_x = float32
    max_y = float32
    max_z = float32

    def __init__(self):
        self.transformation_type = 0

    @classmethod
    def pack(cls, stream, shape):
        shape.batch_count = len(shape.batches)
        super().pack(stream, shape)

    def create_vertex_type(self):
        return numpy.dtype([descriptor.field() for descriptor in self.attribute_descriptors]).newbyteorder('>')


def pack_packet(stream, primitives):
    for primitive in primitives:
        uint8.pack(stream, primitive.primitive_type)
        uint16.pack(stream, len(primitive.vertices))
        primitive.vertices.tofile(stream)

    align(stream, 0x20, b'\x00')


def unpack_packet(stream, vertex_type, size):
    # The entire packet is read into memory at once to improve performance
    packet = stream.read(size)
    primitives = []
    i = 0

    while i < size:
        opcode = packet[i]
        if opcode == 0x00:
            i += 1
            continue
        primitive_type = gx.PrimitiveType(opcode)
        vertex_count = uint16.unpack_from(packet, i + 1)
        vertices = numpy.frombuffer(packet, vertex_type, vertex_count, i + 3)
        primitives.append(Primitive(primitive_type, vertices))
        i += 3 + vertex_count*vertex_type.itemsize

    return primitives


def pack(stream, shapes):
    base = stream.tell()
    header = Header()
    header.shape_count = len(shapes)
    stream.write(b'\x00'*Header.sizeof())

    header.shape_offset = stream.tell() - base
    stream.write(b'\x00'*Shape.sizeof()*len(shapes))

    header.index_offset = stream.tell() - base
    for index in range(len(shapes)):
        uint16.pack(stream, index)

    align(stream, 4)
    header.unknown0_offset = 0

    align(stream, 0x20)
    header.attribute_descriptor_offset = stream.tell() - base
    pack_attribute_descriptors = OffsetPoolPacker(stream, AttributeDescriptorList.pack, stream.tell(), Haystack())
    for shape in shapes:
        shape.attribute_descriptor_offset = pack_attribute_descriptors(shape.attribute_descriptors)

    matrix_indices = []
    matrix_selections = []
    packet_locations = []

    for shape in shapes:
        shape.first_matrix_selection = len(matrix_selections)
        for batch in shape.batches:
            matrix_selection = MatrixSelection()
            matrix_selection.unknown0 = batch.unknown0
            matrix_selection.first = len(matrix_indices)
            matrix_selection.count = len(batch.matrix_table)
            matrix_indices.extend(batch.matrix_table)
            matrix_selections.append(matrix_selection)

    header.matrix_index_offset = stream.tell() - base
    for matrix_index in matrix_indices:
        uint16.pack(stream, matrix_index)

    align(stream, 0x20)
    header.packet_offset = stream.tell() - base
    for shape in shapes:
        shape.first_packet_location = len(packet_locations)
        for batch in shape.batches:
            packet_location = PacketLocation()
            packet_location.offset = stream.tell() - header.packet_offset - base
            pack_packet(stream, batch.primitives)
            packet_location.size = stream.tell() - packet_location.offset - header.packet_offset - base
            packet_locations.append(packet_location)

    header.matrix_selection_offset = stream.tell() - base
    for matrix_selection in matrix_selections:
        MatrixSelection.pack(stream, matrix_selection)

    header.packet_location_offset = stream.tell() - base
    for packet_location in packet_locations:
        PacketLocation.pack(stream, packet_location)

    align(stream, 0x20)
    header.section_size = stream.tell() - base

    stream.seek(base)
    Header.pack(stream, header)

    stream.seek(base + header.shape_offset)
    for shape in shapes:
        Shape.pack(stream, shape)

    stream.seek(base + header.section_size)


def unpack(stream):
    base = stream.tell()
    header = Header.unpack(stream)

    stream.seek(base + header.shape_offset)
    shapes = [Shape.unpack(stream) for _ in range(header.shape_count)]

    stream.seek(base + header.index_offset)
    for index in range(header.shape_count):
        if index != uint16.unpack(stream):
            raise FormatError('invalid index')

    unpack_attribute_descriptors = OffsetPoolUnpacker(stream, AttributeDescriptorList.unpack, base + header.attribute_descriptor_offset)

    for shape in shapes:
        shape.attribute_descriptors = unpack_attribute_descriptors(shape.attribute_descriptor_offset)

    stream.seek(base + header.matrix_selection_offset)
    matrix_selection_count = max(shape.first_matrix_selection + shape.batch_count for shape in shapes)
    matrix_selections = [MatrixSelection.unpack(stream) for _ in range(matrix_selection_count)]

    stream.seek(base + header.matrix_index_offset)
    matrix_index_count = max(selection.first + selection.count for selection in matrix_selections)
    matrix_indices = [uint16.unpack(stream) for _ in range(matrix_index_count)]

    stream.seek(base + header.packet_location_offset)
    packet_count = max(shape.first_packet + shape.batch_count for shape in shapes)
    packet_locations = [PacketLocation.unpack(stream) for _ in range(packet_count)]

    for shape in shapes:
        vertex_type = shape.create_vertex_type()
        shape.batches = [None]*shape.batch_count
        for i in range(shape.batch_count):
            matrix_selection = matrix_selections[shape.first_matrix_selection + i]
            matrix_table = matrix_indices[matrix_selection.first : matrix_selection.first + matrix_selection.count]
            packet_location = packet_locations[shape.first_packet + i]
            stream.seek(base + header.packet_offset + packet_location.offset)
            primitives = unpack_packet(stream, vertex_type, packet_location.size)
            shape.batches[i] = Batch(primitives, matrix_table, matrix_selection.unknown0)

    stream.seek(base + header.section_size)
    return shapes

