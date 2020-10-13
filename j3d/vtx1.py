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
            raise FormatError(f'invalid magic: {header.magic}')
        if header.unknown0_offset is not None:
            logger.warning('unexpected unknown0_offset value: %s', header.unknown0_offset)
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
            raise FormatError(f'invalid vertex attribute: {attribute_format.attribute}')

        return attribute_format


def convert_component_type(component_type):
    if component_type == gx.U8:
        return numpy.uint8
    if component_type == gx.S8:
        return numpy.int8
    if component_type == gx.U16:
        return numpy.uint16
    if component_type == gx.S16:
        return numpy.int16
    if component_type == gx.F32:
        return numpy.float32
    raise ValueError(f'invalid component type: {component_type}')


def convert_position_component_count(component_count):
    if component_count == gx.POS_XY:
        return 2
    if component_count == gx.POS_XYZ:
        return 3
    raise ValueError(f'invalid position component count: {component_count}')


def convert_normal_component_count(component_count):
    if component_count == gx.NRM_XYZ:
        return 3
    raise ValueError(f'invalid normal component count: {component_count}')


def convert_texcoord_component_count(component_count):
    if component_count == gx.TEX_S:
        return 1
    if component_count == gx.TEX_ST:
        return 2
    raise ValueError(f'invalid texcoord component count: {component_count}')


def get_color_element_type(attribute_format):
    if attribute_format.component_type in {gx.RGB8, gx.RGBX8, gx.RGBA8}:
        return numpy.dtype((numpy.uint8, 4))
    if attribute_format.component_type in {gx.RGB565, gx.RGBA4}:
        return numpy.dtype(numpy.uint16).newbyteorder('>')
    if attribute_format.component_type == gx.RGBA6:
        return numpy.dtype(numpy.uint32).newbyteorder('>')
    raise ValueError(f'invalid color component type: {attribute_format.component_type}')


def get_element_type(attribute_format):
    if attribute_format.attribute in gx.VA_CLR:
        return get_color_element_type(attribute_format)

    component_type = convert_component_type(attribute_format.component_type)

    if attribute_format.attribute == gx.VA_POS:
        component_count = convert_position_component_count(attribute_format.component_count)
    elif attribute_format.attribute == gx.VA_NRM:
        component_count = convert_normal_component_count(attribute_format.component_count)
    elif attribute_format.attribute in gx.VA_TEX:
        component_count = convert_texcoord_component_count(attribute_format.component_count)
    else:
        raise ValueError(f'invalid attribute: {attribute_format.attribute}')

    return numpy.dtype((component_type, component_count)).newbyteorder('>')


class AttributeFormatList(TerminatedList):
    element_type = AttributeFormat
    terminator_value = AttributeFormat(gx.VA_NULL, 1, 0, 0)

    @staticmethod
    def terminator_predicate(element):
        return element.attribute == gx.VA_NULL


class Array(numpy.ndarray):

    def __array_finalize__(self, obj):
        if not isinstance(obj, Array):
            return
        self.attribute = obj.attribute
        self.component_type = obj.component_type
        self.component_count = obj.component_count
        self.scale_exponent = obj.scale_exponent

    @staticmethod
    def pack(stream, array):
        array.tofile(stream)

    @classmethod
    def unpack(cls, stream, attribute_format, size):
        element_type = get_element_type(attribute_format)
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
        if array is None:
            return None
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


class SectionData:

    def __init__(self, position_array, normal_array, color_arrays, texcoord_arrays):
        self.position_array = position_array
        self.normal_array = normal_array
        self.color_arrays = color_arrays
        self.texcoord_arrays = texcoord_arrays


def unpack(stream):
    base = stream.tell()
    header = Header.unpack(stream)

    stream.seek(base + header.attribute_format_offset)
    attribute_formats = AttributeFormatList.unpack(stream)
    attribute_format_table = {
        attribute_format.attribute : attribute_format
        for attribute_format in attribute_formats
    }

    # It is not specified how large each array is, so we assume that an array
    # ends when the next array starts (or when the section ends). This is not
    # perfect; padding at the end of an array can be interpreted as being part of
    # the array, and it will not work if two arrays overlap (though nothing
    # suggests that that ever happens).
    array_bounds = []
    array_bounds.append(header.position_offset)
    array_bounds.append(header.normal_offset)
    array_bounds.extend(header.color_offsets)
    array_bounds.extend(header.texcoord_offsets)
    array_bounds.append(header.section_size)
    array_bounds = sorted(filter(None.__ne__, array_bounds))

    def unpack_array(offset, attribute):
        if attribute not in attribute_format_table:
            return None
        attribute_format = attribute_format_table[attribute]
        size = array_bounds[array_bounds.index(offset) + 1] - offset
        stream.seek(base + offset)
        return Array.unpack(stream, attribute_format, size)

    position_array = unpack_array(header.position_offset, gx.VA_POS)
    normal_array = unpack_array(header.normal_offset, gx.VA_NRM)
    color_arrays = list(map(unpack_array, header.color_offsets, gx.VA_CLR))
    texcoord_arrays = list(map(unpack_array, header.texcoord_offsets, gx.VA_TEX))

    stream.seek(base + header.section_size)
    return SectionData(
        position_array=position_array,
        normal_array=normal_array,
        color_arrays=color_arrays,
        texcoord_arrays=texcoord_arrays
    )

