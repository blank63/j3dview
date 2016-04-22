import numpy
from btypes.big_endian import *
import gl
import gx
from OpenGL.GL import *

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
    def unpack(cls,stream):
        header = super().unpack(stream)
        if header.magic != b'SHP1':
            raise FormatError('invalid magic')
        if header.unknown0_offset != 0:
            logger.warning('unknown0_offset different from default')
        return header


class AttributeDescriptor(Struct):
    """Arguments to GXSetVtxDesc."""
    attribute = EnumConverter(uint32,gx.Attribute)
    input_type = EnumConverter(uint32,gx.InputType)

    def __init__(self,attribute,input_type):
        self.attribute = attribute
        self.input_type = input_type

    def field(self):
        if self.attribute == gx.VA_PTNMTXIDX and self.input_type == gx.DIRECT:
            return (gx.VA_PTNMTXIDX.name,numpy.uint8)
        if self.input_type == gx.INDEX8:
            return (self.attribute.name,numpy.uint8)
        if self.input_type == gx.INDEX16:
            return (self.attribute.name,numpy.uint16)

        raise ValueError('invalid attribute descriptor')


class AttributeDescriptorList(TerminatedList):
    element_type = AttributeDescriptor
    terminator_value = element_type(gx.VA_NULL,gx.NONE)

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

    def __init__(self,primitive_type,vertices):
        self.primitive_type = primitive_type
        self.vertices = vertices


class Batch:

    def __init__(self,primitives,matrix_table,unknown0):
        self.primitives = primitives
        self.matrix_table = matrix_table
        self.unknown0 = unknown0


def gl_count_triangles(shape):
    triangle_count = 0

    for primitive in shape.primitives:
        if primitive.primitive_type == gx.TRIANGLES:
            triangle_count += len(primitive.vertices)//3
        elif primitive.primitive_type == gx.TRIANGLESTRIP:
            triangle_count += len(primitive.vertices) - 2
        elif primitive.primitive_type == gx.TRIANGLEFAN:
            triangle_count += len(primitive.vertices) - 2
        elif primitive.primitive_type == gx.QUADS:
            triangle_count += len(primitive.vertices)//2
        else:
            raise ValueError('invalid primitive type')
            
    return triangle_count

    
def gl_create_element_array(shape,element_map,element_count):
    element_array = numpy.empty(element_count,numpy.uint16)
    
    element_index = 0
    vertex_index = 0

    for primitive in shape.primitives:
        if primitive.primitive_type == gx.TRIANGLES:
            for i in range(len(primitive.vertices)//3):
                element_array[element_index + 0] = element_map[vertex_index + 3*i + 0]
                element_array[element_index + 1] = element_map[vertex_index + 3*i + 2]
                element_array[element_index + 2] = element_map[vertex_index + 3*i + 1]
                element_index += 3
        elif primitive.primitive_type == gx.TRIANGLESTRIP:
            for i in range(len(primitive.vertices) - 2):
                element_array[element_index + 0] = element_map[vertex_index + i + 1 - (i % 2)]
                element_array[element_index + 1] = element_map[vertex_index + i + (i % 2)]
                element_array[element_index + 2] = element_map[vertex_index + i + 2]
                element_index += 3
        elif primitive.primitive_type == gx.TRIANGLEFAN:
            for i in range(len(primitive.vertices) - 2):
                element_array[element_index + 0] = element_map[vertex_index]
                element_array[element_index + 1] = element_map[vertex_index + i + 2]
                element_array[element_index + 2] = element_map[vertex_index + i + 1]
                element_index += 3
        elif primitive.primitive_type == gx.QUADS:
            for i in range(0,len(primitive.vertices)//4,4):
                element_array[element_index + 0] = element_map[vertex_index + i]
                element_array[element_index + 1] = element_map[vertex_index + i + 1]
                element_array[element_index + 2] = element_map[vertex_index + i + 2]
                element_array[element_index + 3] = element_map[vertex_index + i + 1]
                element_array[element_index + 4] = element_map[vertex_index + i + 3]
                element_array[element_index + 5] = element_map[vertex_index + i + 2]
                element_index += 6
        else:
            raise ValueError('invalid primitive type')

        vertex_index += len(primitive.vertices)

    return element_array

    
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

    @property
    def attributes(self):
        for descriptor in self.attribute_descriptors:
            yield descriptor.attribute

    @property
    def primitives(self):
        for batch in self.batches:
            yield from batch.primitives

    @classmethod
    def pack(cls,stream,shape):
        shape.batch_count = len(shape.batches)
        super().pack(stream,shape)

    def create_vertex_type(self):
        return numpy.dtype([descriptor.field() for descriptor in self.attribute_descriptors]).newbyteorder('>')

    def gl_init(self,array_table):
        self.gl_hide = False

        self.gl_vertex_array = gl.VertexArray()
        glBindVertexArray(self.gl_vertex_array)

        self.gl_vertex_buffer = gl.Buffer()
        glBindBuffer(GL_ARRAY_BUFFER,self.gl_vertex_buffer)

        self.gl_element_count = 3*gl_count_triangles(self)
        self.gl_element_buffer = gl.Buffer()
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER,self.gl_element_buffer)

        vertex_type =  numpy.dtype([array_table[attribute].field() for attribute in self.attributes])
        vertex_count = sum(len(primitive.vertices) for primitive in self.primitives)
        vertex_array = numpy.empty(vertex_count,vertex_type)

        for attribute in self.attributes:
            array_table[attribute].load(self,vertex_array)

        vertex_array,element_map = numpy.unique(vertex_array,return_inverse=True)
        element_array = gl_create_element_array(self,element_map,self.gl_element_count)

        glBufferData(GL_ARRAY_BUFFER,vertex_array.nbytes,vertex_array,GL_STATIC_DRAW)
        glBufferData(GL_ELEMENT_ARRAY_BUFFER,element_array.nbytes,element_array,GL_STATIC_DRAW)

    def gl_bind(self):
        glBindVertexArray(self.gl_vertex_array)

    def gl_draw(self):
        glDrawElements(GL_TRIANGLES,self.gl_element_count,GL_UNSIGNED_SHORT,None)


def pack_packet(stream,primitives):
    for primitive in primitives:
        uint8.pack(stream,primitive.primitive_type)
        uint16.pack(stream,len(primitive.vertices))
        primitive.vertices.tofile(stream)

    align(stream,0x20,b'\x00')


def unpack_packet(stream,vertex_type,size):
    # The entire packet is read into memory at once for speed
    packet = stream.read(size)
    primitives = []
    i = 0

    while i < size:
        opcode = packet[i]
        if opcode == 0x00:
            i += 1
            continue
        primitive_type = gx.PrimitiveType(opcode)
        vertex_count = uint16.unpack_from(packet,i + 1)
        vertices = numpy.frombuffer(packet,vertex_type,vertex_count,i + 3)
        primitives.append(Primitive(primitive_type,vertices))
        i += 3 + vertex_count*vertex_type.itemsize

    return primitives


class Pool:

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


class CachedOffsetPacker:

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


class CachedOffsetUnpacker:

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


def pack(stream,shapes):
    base = stream.tell()
    header = Header()
    header.shape_count = len(shapes)
    stream.write(b'\x00'*Header.sizeof())

    header.shape_offset = stream.tell() - base
    stream.write(b'\x00'*Shape.sizeof()*len(shapes))

    header.index_offset = stream.tell() - base
    for index in range(len(shapes)):
        uint16.pack(stream,index)

    align(stream,4)
    header.unknown0_offset = 0

    align(stream,0x20)
    header.attribute_descriptor_offset = stream.tell() - base
    pack_attribute_descriptors = CachedOffsetPacker(stream,AttributeDescriptorList.pack,stream.tell(),Pool())
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
        uint16.pack(stream,matrix_index)

    align(stream,0x20)
    header.packet_offset = stream.tell() - base
    for shape in shapes:
        shape.first_packet_location = len(packet_locations)
        for batch in shape.batches:
            packet_location = PacketLocation()
            packet_location.offset = stream.tell() - header.packet_offset - base
            pack_packet(stream,batch.primitives)
            packet_location.size = stream.tell() - packet_location.offset - header.packet_offset - base
            packet_locations.append(packet_location)

    header.matrix_selection_offset = stream.tell() - base
    for matrix_selection in matrix_selections:
        MatrixSelection.pack(stream,matrix_selection)

    header.packet_location_offset = stream.tell() - base
    for packet_location in packet_locations:
        PacketLocation.pack(stream,packet_location)

    align(stream,0x20)
    header.section_size = stream.tell() - base

    stream.seek(base)
    Header.pack(stream,header)

    stream.seek(base + header.shape_offset)
    for shape in shapes:
        Shape.pack(stream,shape)

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

    unpack_attribute_descriptors = CachedOffsetUnpacker(stream,AttributeDescriptorList.unpack,base + header.attribute_descriptor_offset)

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
            matrix_table = matrix_indices[matrix_selection.first:matrix_selection.first + matrix_selection.count]
            packet_location = packet_locations[shape.first_packet + i]
            stream.seek(base + header.packet_offset + packet_location.offset)
            primitives = unpack_packet(stream,vertex_type,packet_location.size)
            shape.batches[i] = Batch(primitives,matrix_table,matrix_selection.unknown0)

    stream.seek(base + header.section_size)
    return shapes

