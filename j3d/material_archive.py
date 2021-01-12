from btypes.big_endian import *
import j3d.mat3
import j3d.tex1


class Header(Struct):
    magic = ByteString(4)
    file_type = ByteString(4)
    file_size = uint32
    section_count = uint32
    subversion = ByteString(4)
    __padding__ = Padding(12)

    def __init__(self):
        self.magic = b'J3D2'
        self.file_type = b'bmt3'
        self.section_count = 2
        self.subversion = b'SVR3'

    @classmethod
    def unpack(cls, stream):
        header = super().unpack(stream)
        if header.magic != b'J3D2':
            raise FormatError(f'invalid magic: {header.magic}')
        if header.file_type != b'bmt3':
            raise FormatError(f'invalid file type: {header.file_type}')
        if header.section_count != 2:
            raise FormatError(f'invalid section count: {header.section_count}')
        if header.subversion != b'SVR3':
            logger.warning(f'unexpected subversion: %s', header.subversion)
        return header


class MaterialArchive:

    def __init__(self, materials, textures):
        self.materials = materials
        self.textures = textures


def pack(stream, material_archive):
    header = Header()
    stream.write(b'\x00'*Header.sizeof())
    j3d.mat3.pack(stream, material_archive.materials, header.subversion)
    j3d.tex1.pack(stream, material_archive.textures)
    header.file_size = stream.tell()
    stream.seek(0)
    Header.pack(stream, header)


def unpack(stream):
    header = Header.unpack(stream)
    materials = j3d.mat3.unpack(stream, header.subversion)
    textures = j3d.tex1.unpack(stream)
    return MaterialArchive(materials, textures)

