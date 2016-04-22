from btypes.big_endian import *
import gx
import gx.texture
import j3d.string_table

import logging
logger = logging.getLogger(__name__)


class Header(Struct):
    magic = ByteString(4)
    section_size = uint32
    texture_count = uint16
    __padding__ = Padding(2)
    texture_offset = uint32
    name_offset = uint32

    def __init__(self):
        self.magic = b'TEX1'

    @classmethod
    def unpack(cls,stream):
        header = super().unpack(stream)
        if header.magic != b'TEX1':
            raise FormatError('invalid magic')
        return header


class Texture(gx.texture.Texture,Struct):
    image_format = EnumConverter(uint8,gx.TextureFormat)
    unknown0 = uint8
    width = uint16
    height = uint16
    wrap_s = EnumConverter(uint8,gx.WrapMode)
    wrap_t = EnumConverter(uint8,gx.WrapMode)
    unknown1 = uint8
    palette_format = EnumConverter(uint8,gx.PaletteFormat)
    palette_entry_count = uint16
    palette_offset = uint32
    use_mipmapping = bool8
    __padding__ = Padding(3,b'\x00')
    minification_filter = EnumConverter(uint8,gx.FilterMode)
    magnification_filter = EnumConverter(uint8,gx.FilterMode)
    minimum_lod = FixedPointConverter(sint8,1/8)
    maximum_lod = FixedPointConverter(sint8,1/8)
    level_count = uint8
    unknown2 = uint8
    lod_bias = FixedPointConverter(sint16,1/100)
    image_offset = uint32

    def __init__(self):
        super().__init__()
        self.unknown0 = 1
        self.unknown1 = 0
        self.unknown2 = 0

    @classmethod
    def pack(cls,stream,texture):
        texture.level_count = len(texture.images)
        texture.use_mipmapping = texture.minification_filter in {gx.NEAR_MIP_NEAR,gx.LIN_MIP_NEAR,gx.NEAR_MIP_LIN,gx.LIN_MIP_LIN}
        super().pack(stream,texture)

    @classmethod
    def unpack(cls,stream):
        texture = super().unpack(stream)
        if texture.unknown0 not in {0x00,0x01,0x02,0xCC}:
            logger.warning('unknown0 different from default')
        if texture.unknown1 not in {0,1}:
            logger.warning('unknown1 different from default')
        return texture


class CachedOffsetPacker:

    def __init__(self,stream,pack_function,default_offset_table=None):
        self.stream = stream
        self.pack_function = pack_function
        self.offset_table = default_offset_table if default_offset_table is not None else {}

    def __call__(self,*args):
        if args in self.offset_table:
            return self.offset_table[args]

        offset = self.stream.tell()
        self.pack_function(self.stream,*args)
        self.offset_table[args] = offset
        return offset


class CachedOffsetUnpacker:

    def __init__(self,stream,unpack_function):
        self.stream = stream
        self.unpack_function = unpack_function
        self.argument_table = {}
        self.value_table = {}

    def __call__(self,offset,*args):
        if offset in self.value_table:
            if args != self.argument_table[offset]:
                raise ValueError('inconsistent arguments for same offset')
            return self.value_table[offset]

        self.stream.seek(offset)
        value = self.unpack_function(self.stream,*args)
        self.argument_table[offset] = args
        self.value_table[offset] = value
        return value


def pack(stream,textures):
    base = stream.tell()
    header = Header()
    header.texture_count = len(textures)
    stream.write(b'\x00'*Header.sizeof())

    align(stream,0x20)
    header.texture_offset = stream.tell() - base
    stream.write(b'\x00'*Texture.sizeof()*len(textures))

    pack_palette = CachedOffsetPacker(stream,gx.texture.pack_palette)
    pack_images = CachedOffsetPacker(stream,gx.texture.pack_images)

    for i,texture in enumerate(textures):
        texture_offset = base + header.texture_offset + i*Texture.sizeof()

        if texture.palette is None:
            texture.palette_offset = stream.tell() - texture_offset
            continue

        texture.palette_offset = pack_palette(texture.palette) - texture_offset

    for i,texture in enumerate(textures):
        texture_offset = base + header.texture_offset + i*Texture.sizeof()
        texture.image_offset = pack_images(texture.images) - texture_offset

    header.name_offset = stream.tell() - base
    j3d.string_table.pack(stream,(texture.name for texture in textures))

    align(stream,0x20)
    header.section_size = stream.tell() - base
    stream.seek(base)
    Header.pack(stream,header)

    stream.seek(base + header.texture_offset)
    for texture in textures:
        Texture.pack(stream,texture)

    stream.seek(base + header.section_size)


def unpack(stream):
    base = stream.tell()
    header = Header.unpack(stream)

    stream.seek(base + header.texture_offset)
    textures = [Texture.unpack(stream) for _ in range(header.texture_count)]

    unpack_palette = CachedOffsetUnpacker(stream,gx.texture.unpack_palette)
    unpack_images = CachedOffsetUnpacker(stream,gx.texture.unpack_images)

    for i,texture in enumerate(textures):
        if texture.palette_entry_count == 0:
            texture.palette = None
            continue

        texture_offset = base + header.texture_offset + i*Texture.sizeof()
        palette_offset = texture_offset + texture.palette_offset
        texture.palette = unpack_palette(palette_offset,texture.palette_format,texture.palette_entry_count)

    for i,texture in enumerate(textures):
        texture_offset = base + header.texture_offset + i*Texture.sizeof()
        image_offset = texture_offset + texture.image_offset
        texture.images = unpack_images(image_offset,texture.image_format,texture.width,texture.height,texture.level_count)

    stream.seek(base + header.name_offset)
    names = j3d.string_table.unpack(stream)
    for texture,name in zip(textures,names):
        texture.name = name

    stream.seek(base + header.section_size)
    return textures

