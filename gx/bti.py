from btypes.big_endian import *
from btypes.utils import OffsetPoolPacker, OffsetPoolUnpacker
import gx
import gx.texture

import logging
logger = logging.getLogger(__name__)


class Texture(Struct):
    image_format = EnumConverter(uint8, gx.TextureFormat)
    unknown0 = uint8
    width = uint16
    height = uint16
    wrap_s = EnumConverter(uint8, gx.WrapMode)
    wrap_t = EnumConverter(uint8, gx.WrapMode)
    unknown1 = uint8
    palette_format = EnumConverter(uint8, gx.PaletteFormat)
    palette_entry_count = uint16
    palette_offset = uint32
    use_mipmapping = bool8
    __padding__ = Padding(3, b'\x00')
    minification_filter = EnumConverter(uint8, gx.FilterMode)
    magnification_filter = EnumConverter(uint8, gx.FilterMode)
    minimum_lod = FixedPointConverter(sint8, 1/8)
    maximum_lod = FixedPointConverter(sint8, 1/8)
    level_count = uint8
    unknown2 = uint8
    lod_bias = FixedPointConverter(sint16, 1/100)
    image_offset = uint32

    def __init__(self):
        super().__init__()
        self.unknown0 = 1
        self.unknown1 = 0
        self.unknown2 = 0

    @classmethod
    def pack(cls, stream, texture):
        texture.level_count = len(texture.images)
        texture.use_mipmapping = texture.minification_filter in {gx.NEAR_MIP_NEAR, gx.LIN_MIP_NEAR, gx.NEAR_MIP_LIN, gx.LIN_MIP_LIN}
        super().pack(stream, texture)

    @classmethod
    def unpack(cls, stream):
        texture = super().unpack(stream)
        texture.palette = None
        if texture.unknown0 not in {0x00, 0x01, 0x02, 0xCC}:
            logger.warning('unknown0 different from default')
        if texture.unknown1 not in {0, 1}:
            logger.warning('unknown1 different from default')
        return texture


def pack_textures(stream, textures):
    base = stream.tell()

    stream.write(b'\x00'*Texture.sizeof()*len(textures))

    pack_palette = OffsetPoolPacker(stream, gx.texture.pack_palette)
    pack_images = OffsetPoolPacker(stream, gx.texture.pack_images)

    for i, texture in enumerate(textures):
        texture_offset = base + i*Texture.sizeof()

        if texture.palette is None:
            texture.palette_offset = stream.tell() - texture_offset
            continue

        texture.palette_offset = pack_palette(texture.palette) - texture_offset

    for i, texture in enumerate(textures):
        texture_offset = base + i*Texture.sizeof()
        texture.image_offset = pack_images(texture.images) - texture_offset

    end = stream.tell()

    stream.seek(base)
    for texture in textures:
        Texture.pack(stream, texture)

    stream.seek(end)
    return


def unpack_textures(stream, texture_count):
    base = stream.tell()

    textures = [Texture.unpack(stream) for _ in range(texture_count)]

    unpack_palette = OffsetPoolUnpacker(stream, gx.texture.unpack_palette)
    unpack_images = OffsetPoolUnpacker(stream, gx.texture.unpack_images)

    for i, texture in enumerate(textures):
        if texture.palette_entry_count == 0: continue
        texture_offset = base + i*Texture.sizeof()
        palette_offset = texture_offset + texture.palette_offset
        texture.palette = unpack_palette(palette_offset, texture.palette_format, texture.palette_entry_count)

    for i, texture in enumerate(textures):
        texture_offset = base + i*Texture.sizeof()
        image_offset = texture_offset + texture.image_offset
        texture.images = unpack_images(image_offset, texture.image_format, texture.width, texture.height, texture.level_count)

    return textures


def pack(stream, texture):
    pack_textures(stream, [texture])


def unpack(stream):
    return unpack_textures(stream, 1)[0]

