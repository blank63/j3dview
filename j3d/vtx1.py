from collections import defaultdict
import numpy
from OpenGL.GL import *
from btypes.big_endian import *
import gx
from j3d.opengl import *

import logging
logger = logging.getLogger(__name__)


class Header(Struct):
    magic = ByteString(4)
    section_size = uint32
    attribute_format_offset = uint32
    position_offset = uint32
    normal_offset = uint32
    unknown0_offset = uint32 # NBT?
    color_offsets = Array(uint32,2)
    texcoord_offsets = Array(uint32,8)

    def __init__(self):
        self.magic = b'VTX1'
        self.unknown0_offset = 0

    @classmethod
    def unpack(cls,stream):
        header = super().unpack(stream)
        if header.magic != b'VTX1':
            raise FormatError('invalid magic')
        if header.unknown0_offset != 0:
            logger.warning('unknown0_offset different from default')
        return header


class AttributeFormat(Struct):
    """ Arguments to GXSetVtxAttrFmt."""
    attribute = EnumConverter(uint32,gx.Attribute)
    component_count = uint32
    component_type = uint32
    scale_exponent = uint8
    __padding__ = Padding(3)

    def __init__(self,attribute,component_count,component_type,scale_exponent):
        self.attribute = attribute
        self.component_count = component_count
        self.component_type = component_type
        self.scale_exponent = scale_exponent


class AttributeFormatList(TerminatedList):
    element_type = AttributeFormat
    terminator_value = AttributeFormat(gx.VA_NULL,1,0,0)

    @staticmethod
    def terminator_predicate(element):
        return element.attribute == gx.VA_NULL


class Array(numpy.ndarray):

    @staticmethod
    def create_element_type(component_type,component_count):
        return numpy.dtype((component_type.numpy_type,component_count.actual_value)).newbyteorder('>')

    def __array_finalize__(self,obj):
        if not isinstance(obj,Array): return
        self.attribute = obj.attribute
        self.component_type = obj.component_type
        self.component_count = obj.component_count
        self.scale_exponent = obj.scale_exponent

    def gl_convert(self):
        array = numpy.asfarray(self,numpy.float32)

        if self.component_type != gx.F32 and self.scale_exponent != 0:
            array *= 2**(-self.scale_exponent)

        array = array.view(GLArray)
        array.attribute = self.attribute
        array.component_type = GL_FLOAT
        array.component_count = self.shape[1]
        array.normalize = False
        return array


class ColorArray(numpy.ndarray):

    @property
    def has_alpha(self):
        return self.component_count == gx.CLR_RGBA and self.component_type in {gx.RGBA8,gx.RGBA4,gx.RGBA6}

    @staticmethod
    def create_element_type(component_type,component_count):
        if component_type in {gx.RGB8,gx.RGBX8,gx.RGBA8}:
            return numpy.dtype((numpy.uint8,4))
        if component_type in {gx.RGB565,gx.RGBA4}:
            return numpy.dtype(numpy.uint16).newbyteorder('>')
        if component_type == gx.RGBA6:
            return numpy.dtype(numpy.uint32).newbyteorder('>')

        raise ValueError('invalid color component type')

    def gl_convert(self):
        if self.component_type in {gx.RGB8,gx.RGBX8,gx.RGBA8}:
            array = self
        
        if self.component_type == gx.RGB565:
            array = numpy.empty((element_count,4),numpy.uint8)
            array[:,0] = ((self >> 8) & 0xF8) | ((self >> 13) & 0x7)
            array[:,1] = ((self >> 3) & 0xFC) | ((self >> 9) & 0x3)
            array[:,2] = ((self << 3) & 0xF8) | ((self >> 2) & 0x7)
            array[:,3] = 0xFF

        if self.component_type == gx.RGBA4:
            array = numpy.empty((element_count,4),numpy.uint8)
            array[:,0] = ((self >> 8) & 0xF0) | ((self >> 12) & 0xF)
            array[:,1] = ((self >> 4) & 0xF0) | ((self >> 8) & 0xF)
            array[:,2] = (self & 0xF0) | ((self >> 4) & 0xF)
            array[:,3] = ((self << 4) & 0xF0) | (self & 0xF)

        if self.component_type == gx.RGBA6:
            array = numpy.empty((element_count,4),numpy.uint8)
            array[:,0] = ((self >> 16) & 0xFC) | ((self >> 22) & 0x3)
            array[:,1] = ((self >> 10) & 0xFC) | ((self >> 16) & 0x3)
            array[:,2] = ((self >> 4) & 0xFC) | ((self >> 10) & 0x3)
            array[:,3] = ((self << 2) & 0xFC) | ((self >> 4) & 0x3)

        array = array.view(GLArray)
        array.attribute = self.attribute
        array.component_type = GL_UNSIGNED_BYTE
        array.component_count = 4 if self.has_alpha else 3
        array.normalize = True
        return array


class GLArray(numpy.ndarray):

    def field(self):
        return (self.attribute.name,self.dtype,self.shape[1])

    def load(self,shape,vertex_array):
        index_array = numpy.concatenate([primitive.vertices[self.attribute.name] for primitive in shape.primitives])
        numpy.take(self,index_array,0,vertex_array[self.attribute.name])
        location = ATTRIBUTE_LOCATION_TABLE[self.attribute]
        glEnableVertexAttribArray(location)
        vertex_type = vertex_array.dtype
        stride = vertex_type.itemsize
        offset = vertex_type.fields[self.attribute.name][1]
        glVertexAttribPointer(location,self.component_count,self.component_type,self.normalize,stride,GLvoidp(offset))


def unpack_array(stream,attribute_format,size):
    if attribute_format.attribute == gx.VA_POS:
        component_type = gx.ComponentType(attribute_format.component_type)
        component_count = gx.PositionComponentCount(attribute_format.component_count)
        array_type = Array
    elif attribute_format.attribute == gx.VA_NRM:
        component_type = gx.ComponentType(attribute_format.component_type)
        component_count = gx.NormalComponentCount(attribute_format.component_count)
        array_type = Array
    elif attribute_format.attribute in gx.VA_CLR:
        component_type = gx.ColorComponentType(attribute_format.component_type)
        component_count = gx.ColorComponentCount(attribute_format.component_count)
        array_type = ColorArray
    elif attribute_format.attribute in gx.VA_TEX:
        component_type = gx.ComponentType(attribute_format.component_type)
        component_count = gx.TexCoordComponentCount(attribute_format.component_count)
        array_type = Array
    else:
        raise FormatError('invalid vertex attribute')

    element_type = array_type.create_element_type(component_type,component_count)
    element_count = size//element_type.itemsize
    array = numpy.fromfile(stream,element_type,element_count).view(array_type)
    array.attribute = attribute_format.attribute
    array.component_type = component_type
    array.component_count = component_count
    array.scale_exponent = attribute_format.scale_exponent
    return array


def pack(stream,array_table):
    base = stream.tell()
    header = Header()
    stream.write(b'\x00'*Header.sizeof())

    offset_table = defaultdict(int)
    arrays = [array_table[attribute] for attribute in gx.Attribute if attribute in array_table]

    header.attribute_format_offset = stream.tell() - base
    AttributeFormatList.pack(stream,arrays)

    for array in arrays:
        align(stream,0x20)
        offset_table[array.attribute] = stream.tell() - base
        array.tofile(stream)

    header.position_offset = offset_table[gx.VA_POS]
    header.normal_offset = offset_table[gx.VA_NRM]
    header.color_offsets = [offset_table[attribute] for attribute in gx.VA_CLR]
    header.texcoord_offsets = [offset_table[attribute] for attribute in gx.VA_TEX]

    align(stream,0x20)
    header.section_size = stream.tell() - base
    stream.seek(base)
    Header.pack(stream,header)
    stream.seek(base + header.section_size)


def unpack(stream):
    base = stream.tell()
    header = Header.unpack(stream)

    offset_table = {}
    array_table = {}

    offset_table[gx.VA_POS] = header.position_offset
    offset_table[gx.VA_NRM] = header.normal_offset
    offset_table.update(zip(gx.VA_CLR,header.color_offsets))
    offset_table.update(zip(gx.VA_TEX,header.texcoord_offsets))

    stream.seek(base + header.attribute_format_offset)
    attribute_formats = AttributeFormatList.unpack(stream)

    for attribute_format in attribute_formats:
        array_offset = offset_table[attribute_format.attribute]
        size = min((offset for offset in offset_table.values() if offset > array_offset),default=header.section_size) - array_offset
        stream.seek(base + array_offset)
        array_table[attribute_format.attribute] = unpack_array(stream,attribute_format,size)

    stream.seek(base + header.section_size)
    return array_table

