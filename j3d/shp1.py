import numpy
from btypes.big_endian import *
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
            raise FormatError(f'invalid magic: {header.magic}')
        if header.unknown0_offset != 0:
            logger.warning('unexpected unknown0_offset value: %s', header.unknown0_offset)
        return header


class AttributeDescriptor(Struct):
    """Arguments to GXSetVtxDesc."""
    attribute = EnumConverter(uint32, gx.Attribute)
    input_type = EnumConverter(uint32, gx.InputType)

    def __init__(self, attribute, input_type):
        self.attribute = attribute
        self.input_type = input_type


class AttributeDescriptorList(TerminatedList):
    element_type = AttributeDescriptor
    terminator_value = element_type(gx.VA_NULL, gx.NONE)

    @staticmethod
    def terminator_predicate(element):
        return element.attribute == gx.VA_NULL


class MatrixSelection(Struct):
    unknown0 = uint16 # position/normal matrix for texture matrices? noclip.website: use matrix index
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


def get_attribute_type(attribute_descriptor):
    if attribute_descriptor.input_type == gx.INDEX8:
        return numpy.uint8
    if attribute_descriptor.input_type == gx.INDEX16:
        return numpy.uint16
    if attribute_descriptor.input_type == gx.DIRECT:
        if attribute_descriptor.attribute == gx.VA_PTNMTXIDX:
            return numpy.uint8
        if attribute_descriptor.attribute in gx.VA_TEXMTXIDX:
            return numpy.uint8
        raise ValueError(f'invalid direct attribute: {attribute_descriptor.attribute}')
    raise ValueError(f'invalid input type: {attribute_descriptor.input_type}')


def get_vertex_type(attribute_descriptors):
    return numpy.dtype([
        (descriptor.attribute.name, get_attribute_type(descriptor))
        for descriptor in attribute_descriptors
    ]).newbyteorder('>')


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


class Haystack:

    def __init__(self):
        self.keys = []
        self.values = []

    def __getitem__(self, key):
        try:
            index = self.keys.index(key)
        except ValueError:
            raise KeyError(key)
        return self.values[index]

    def __setitem__(self, key, value):
        try:
            index = self.keys.index(key)
        except ValueError:
            self.keys.append(key)
            self.values.append(value)
        else:
            self.values[index] = value

    def __contains__(self, key):
        return key in self.keys


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
    deduplicate_table = Haystack()
    for shape in shapes:
        if shape.attribute_descriptors not in deduplicate_table:
            offset = stream.tell() - base - header.attribute_descriptor_offset
            deduplicate_table[shape.attribute_descriptors] = offset
            AttributeDescriptorList.pack(stream, shape.attribute_descriptors)
        shape.attribute_descriptor_offset = deduplicate_table[shape.attribute_descriptors]

    matrix_indices = []
    matrix_selections = []
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
    packet_locations = []
    for shape in shapes:
        shape.first_packet_location = len(packet_locations)
        for batch in shape.batches:
            offset = stream.tell()
            pack_packet(stream, batch.primitives)
            packet_location = PacketLocation()
            packet_location.offset = offset - header.packet_offset - base
            packet_location.size = stream.tell() - offset
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

    duplicate_table = {}
    for shape in shapes:
        offset = base + header.attribute_descriptor_offset + shape.attribute_descriptor_offset
        if offset not in duplicate_table:
            stream.seek(offset)
            attribute_descriptors = AttributeDescriptorList.unpack(stream)
            duplicate_table[offset] = attribute_descriptors
        shape.attribute_descriptors = duplicate_table[offset]

    stream.seek(base + header.matrix_selection_offset)
    count = max(shape.first_matrix_selection + shape.batch_count for shape in shapes)
    matrix_selections = [MatrixSelection.unpack(stream) for _ in range(count)]

    stream.seek(base + header.matrix_index_offset)
    count = max(selection.first + selection.count for selection in matrix_selections)
    matrix_indices = [uint16.unpack(stream) for _ in range(count)]

    stream.seek(base + header.packet_location_offset)
    count = max(shape.first_packet + shape.batch_count for shape in shapes)
    packet_locations = [PacketLocation.unpack(stream) for _ in range(count)]

    for shape in shapes:
        vertex_type = get_vertex_type(shape.attribute_descriptors)
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

