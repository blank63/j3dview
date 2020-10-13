from btypes.big_endian import *
import gx
import gx.texture
import logging

logger = logging.getLogger(__name__)


MIPMAP_FILTERS = {
    gx.NEAR_MIP_NEAR,
    gx.LIN_MIP_NEAR,
    gx.NEAR_MIP_LIN,
    gx.LIN_MIP_LIN
}


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
        texture.use_mipmapping = texture.minification_filter in MIPMAP_FILTERS
        super().pack(stream, texture)

    @classmethod
    def unpack(cls, stream):
        texture = super().unpack(stream)
        texture.palette = None
        if texture.use_mipmapping != (texture.minification_filter in MIPMAP_FILTERS):
            logger.warning('unexpected use_mipmapping value: %s', texture.use_mipmapping)
        if texture.unknown0 not in {0x00, 0x01, 0x02, 0xCC}:
            logger.warning('unexpected unknown0 value: %s', texture.unknown0)
        if texture.unknown1 not in {0, 1}:
            logger.warning('unexpected unknown1 value: %s', texture.unknown1)
        return texture


def pack_textures(stream, textures):
    base = stream.tell()

    stream.write(b'\x00'*Texture.sizeof()*len(textures))

    deduplicate_table = {}
    for i, texture in enumerate(textures):
        texture_offset = base + i*Texture.sizeof()
        if texture.palette is None:
            texture.palette_offset = stream.tell() - texture_offset
            continue
        key = id(texture.palette)
        if key not in deduplicate_table:
            deduplicate_table[key] = stream.tell()
            gx.texture.pack_palette(stream, texture.palette)
        texture.palette_offset = deduplicate_table[key] - texture_offset

    deduplicate_table = {}
    for i, texture in enumerate(textures):
        texture_offset = base + i*Texture.sizeof()
        key = id(texture.images)
        if key not in deduplicate_table:
            deduplicate_table[key] = stream.tell()
            gx.texture.pack_images(stream, texture.images)
        texture.image_offset = deduplicate_table[key] - texture_offset

    end = stream.tell()

    stream.seek(base)
    for texture in textures:
        Texture.pack(stream, texture)

    stream.seek(end)
    return


def unpack_textures(stream, texture_count):
    base = stream.tell()

    textures = [Texture.unpack(stream) for _ in range(texture_count)]

    duplicate_table = {}
    for i, texture in enumerate(textures):
        if texture.palette_entry_count == 0:
            continue
        texture_offset = base + i*Texture.sizeof()
        palette_offset = texture_offset + texture.palette_offset
        palette_attributes = (texture.palette_format, texture.palette_entry_count)
        key = (palette_offset, palette_attributes)
        if key not in duplicate_table:
            stream.seek(palette_offset)
            palette = gx.texture.unpack_palette(stream, *palette_attributes)
            duplicate_table[key] = palette
        texture.palette = duplicate_table[key]

    duplicate_table = {}
    for i, texture in enumerate(textures):
        texture_offset = base + i*Texture.sizeof()
        image_offset = texture_offset + texture.image_offset
        image_attributes = (texture.image_format, texture.width, texture.height, texture.level_count)
        key = (image_offset, image_attributes)
        if key not in duplicate_table:
            stream.seek(image_offset)
            images = gx.texture.unpack_images(stream, *image_attributes)
            duplicate_table[key] = images
        texture.images = duplicate_table[key]

    return textures


def pack(stream, texture):
    pack_textures(stream, [texture])


def unpack(stream):
    return unpack_textures(stream, 1)[0]

