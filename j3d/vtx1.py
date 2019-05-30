from collections import defaultdict
import numpy
from btypes.big_endian import *
import gx

import logging
logger = logging.getLogger(__name__)

offset32 = NoneableConverter(uint32, 0)


class Header(Struct):
    magic = ByteString(4)
    section_size = uint32
    attribute_format_offset = offset32
    position_offset = offset32
    normal_offset = offset32
    unknown0_offset = offset32 # NBT?
    color_offsets = Array(offset32, 2)
    texcoord_offsets = Array(offset32, 8)

    def __init__(self):
        self.magic = b'VTX1'
        self.unknown0_offset = None

    @classmethod
    def unpack(cls, stream):
        header = super().unpack(stream)
        if header.magic != b'VTX1':
            raise FormatError('invalid magic')
        if header.unknown0_offset is not None:
            logger.warning('unknown0_offset different from default')
        return header


class AttributeFormat(Struct):
    """ Arguments to GXSetVtxAttrFmt."""
    attribute = EnumConverter(uint32, gx.Attribute)
    component_count = uint32
    component_type = uint32
    scale_exponent = uint8
    __padding__ = Padding(3)

    def __init__(self, attribute, component_count, component_type, scale_exponent):
        self.attribute = attribute
        self.component_count = component_count
        self.component_type = component_type
        self.scale_exponent = scale_exponent

    @classmethod
    def unpack(cls, stream):
        attribute_format = super().unpack(stream)

        if attribute_format.attribute == gx.VA_NULL:
            pass
        elif attribute_format.attribute == gx.VA_POS:
            attribute_format.component_type = gx.ComponentType(attribute_format.component_type)
            attribute_format.component_count = gx.PositionComponentCount(attribute_format.component_count)
        elif attribute_format.attribute == gx.VA_NRM:
            attribute_format.component_type = gx.ComponentType(attribute_format.component_type)
            attribute_format.component_count = gx.NormalComponentCount(attribute_format.component_count)
        elif attribute_format.attribute in gx.VA_CLR:
            attribute_format.component_type = gx.ColorComponentType(attribute_format.component_type)
            attribute_format.component_count = gx.ColorComponentCount(attribute_format.component_count)
        elif attribute_format.attribute in gx.VA_TEX:
            attribute_format.component_type = gx.ComponentType(attribute_format.component_type)
            attribute_format.component_count = gx.TexCoordComponentCount(attribute_format.component_count)
        else:
            raise FormatError('invalid vertex attribute')

        return attribute_format

    def create_element_type(self):
        if self.component_type is gx.RGB8 or self.component_type is gx.RGBX8 or self.component_type is gx.RGBA8:
            return numpy.dtype((numpy.uint8, 4))
        if self.component_type is gx.RGB565 or self.component_type is gx.RGBA4:
            return numpy.dtype(numpy.uint16).newbyteorder('>')
        if self.component_type is gx.RGBA6:
            return numpy.dtype(numpy.uint32).newbyteorder('>')

        return numpy.dtype((self.component_type.numpy_type, self.component_count.actual_value)).newbyteorder('>')


class AttributeFormatList(TerminatedList):
    element_type = AttributeFormat
    terminator_value = AttributeFormat(gx.VA_NULL, 1, 0, 0)

    @staticmethod
    def terminator_predicate(element):
        return element.attribute == gx.VA_NULL


class Array(numpy.ndarray):

    def __array_finalize__(self, obj):
        if not isinstance(obj, Array): return
        self.attribute = obj.attribute
        self.component_type = obj.component_type
        self.component_count = obj.component_count
        self.scale_exponent = obj.scale_exponent

    @staticmethod
    def pack(stream, array):
        array.tofile(stream)

    @classmethod
    def unpack(cls, stream, attribute_format, size):
        element_type = attribute_format.create_element_type()
        element_count = size//element_type.itemsize

        array = numpy.fromfile(stream, element_type, element_count).view(cls)
        array.attribute = attribute_format.attribute
        array.component_type = attribute_format.component_type
        array.component_count = attribute_format.component_count
        array.scale_exponent = attribute_format.scale_exponent
        return array


def pack(stream, position_array, normal_array, color_arrays, texcoord_arrays):
    base = stream.tell()
    header = Header()
    stream.write(b'\x00'*Header.sizeof())

    header.attribute_format_offset = stream.tell() - base
    arrays = [position_array, normal_array] + color_arrays + texcoord_arrays
    AttributeFormatList.pack(stream, filter(None.__ne__, arrays))

    def pack_array(array):
        if array is None: return None
        align(stream, 0x20)
        offset = stream.tell() - base
        Array.pack(stream, array)
        return offset

    header.position_offset = pack_array(position_array)
    header.normal_offset = pack_array(normal_array)
    header.color_offsets = list(map(pack_array, color_arrays))
    header.texcoord_offsets = list(map(pack_array, texcoord_arrays))

    align(stream, 0x20)
    header.section_size = stream.tell() - base
    stream.seek(base)
    Header.pack(stream, header)
    stream.seek(base + header.section_size)


def unpack(stream):
    base = stream.tell()
    header = Header.unpack(stream)

    stream.seek(base + header.attribute_format_offset)
    attribute_formats = AttributeFormatList.unpack(stream)
    attribute_format_table = {attribute_format.attribute : attribute_format for attribute_format in attribute_formats}

    array_bounds = []
    array_bounds.append(header.position_offset)
    array_bounds.append(header.normal_offset)
    array_bounds.extend(header.color_offsets)
    array_bounds.extend(header.texcoord_offsets)
    array_bounds.append(header.section_size)
    array_bounds = sorted(filter(None.__ne__, array_bounds))

    def unpack_array(offset, attribute):
        attribute_format = attribute_format_table.get(attribute)
        if attribute_format is None: return None
        size = array_bounds[array_bounds.index(offset) + 1] - offset
        stream.seek(base + offset)
        return Array.unpack(stream, attribute_format, size)

    position_array = unpack_array(header.position_offset, gx.VA_POS)
    normal_array = unpack_array(header.normal_offset, gx.VA_NRM)
    color_arrays = list(map(unpack_array, header.color_offsets, gx.VA_CLR))
    texcoord_arrays = list(map(unpack_array, header.texcoord_offsets, gx.VA_TEX))

    stream.seek(base + header.section_size)
    return position_array, normal_array, color_arrays, texcoord_arrays

