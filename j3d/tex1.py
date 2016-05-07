from btypes.big_endian import *
import gx.bti
import j3d.string_table


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


def pack(stream,textures):
    base = stream.tell()
    header = Header()
    header.texture_count = len(textures)
    stream.write(b'\x00'*Header.sizeof())

    align(stream,0x20)
    header.texture_offset = stream.tell() - base
    gx.bti.pack_textures(stream,textures)

    header.name_offset = stream.tell() - base
    j3d.string_table.pack(stream,(texture.name for texture in textures))

    align(stream,0x20)
    header.section_size = stream.tell() - base
    stream.seek(base)
    Header.pack(stream,header)
    stream.seek(base + header.section_size)


def unpack(stream):
    base = stream.tell()
    header = Header.unpack(stream)

    stream.seek(base + header.texture_offset)
    textures = gx.bti.unpack_textures(stream,header.texture_count)

    stream.seek(base + header.name_offset)
    names = j3d.string_table.unpack(stream)
    for texture,name in zip(textures,names):
        texture.name = name

    stream.seek(base + header.section_size)
    return textures

