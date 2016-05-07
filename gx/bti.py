from btypes.big_endian import *
import gx
import gx.texture

import logging
logger = logging.getLogger(__name__)


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
        texture.palette = None
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


def pack_textures(stream,textures):
    base = stream.tell()

    stream.write(b'\x00'*Texture.sizeof()*len(textures))

    pack_palette = CachedOffsetPacker(stream,gx.texture.pack_palette)
    pack_images = CachedOffsetPacker(stream,gx.texture.pack_images)

    for i,texture in enumerate(textures):
        texture_offset = base + i*Texture.sizeof()

        if texture.palette is None:
            texture.palette_offset = stream.tell() - texture_offset
            continue

        texture.palette_offset = pack_palette(texture.palette) - texture_offset

    for i,texture in enumerate(textures):
        texture_offset = base + i*Texture.sizeof()
        texture.image_offset = pack_images(texture.images) - texture_offset

    end = stream.tell() #<-?

    stream.seek(base)
    for texture in textures:
        Texture.pack(stream,texture)

    stream.seek(end)
    return


def unpack_textures(stream,texture_count):
    base = stream.tell()

    textures = [Texture.unpack(stream) for _ in range(texture_count)]

    unpack_palette = CachedOffsetUnpacker(stream,gx.texture.unpack_palette)
    unpack_images = CachedOffsetUnpacker(stream,gx.texture.unpack_images)

    for i,texture in enumerate(textures):
        if texture.palette_entry_count == 0: continue
        texture_offset = base + i*Texture.sizeof()
        palette_offset = texture_offset + texture.palette_offset
        texture.palette = unpack_palette(palette_offset,texture.palette_format,texture.palette_entry_count)

    for i,texture in enumerate(textures):
        texture_offset = base + i*Texture.sizeof()
        image_offset = texture_offset + texture.image_offset
        texture.images = unpack_images(image_offset,texture.image_format,texture.width,texture.height,texture.level_count)

    return textures


def pack(stream,texture):
    pack_textures(stream,[texture])


def unpack(stream):
    return unpack_textures(stream,1)[0]

