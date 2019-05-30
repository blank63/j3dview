from btypes.big_endian import *
import gx
import j3d.inf1
import j3d.vtx1
import j3d.evp1
import j3d.drw1
import j3d.jnt1
import j3d.shp1
import j3d.mat3
import j3d.mdl3
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

    @classmethod
    def unpack(cls, stream):
        header = super().unpack(stream)

        if header.magic != b'J3D2':
            raise FormatError('invalid magic')

        if header.file_type == b'bmd3':
            expected_section_count = 8
            expected_subversions = {b'SVR3', b'\xFF\xFF\xFF\xFF'}
        elif header.file_type == b'bdl4':
            expected_section_count = 9
            expected_subversions = {b'SVR3'}
        else:
            raise FormatError('invalid file type')

        if header.section_count != expected_section_count:
            raise FormatError('invalid section count')

        if header.subversion not in expected_subversions:
            raise FormatError('invalid subversion')

        return header


class Model:
    pass


def skip_section(stream, magic):
    if stream.read(4) != magic:
        raise FormatError('invalid magic')
    section_size = uint32.unpack(stream)
    stream.seek(section_size - 8, SEEK_CUR)


def pack(stream, model, file_type):
    if file_type in {'bmd', '.bmd'}:
        file_type = b'bmd3'
        section_count = 8
    elif file_type in {'bdl', '.bdl'}:
        file_type = b'bdl4'
        section_count = 9
    else:
        raise ValueError('invalid file type')

    header = Header()
    header.file_type = file_type
    header.section_count = section_count
    header.subversion = model.subversion
    stream.write(b'\x00'*Header.sizeof())

    shape_batch_count = sum(len(shape.batches) for shape in model.shapes)
    vertex_position_count = len(model.position_array)

    j3d.inf1.pack(stream, model.scene_graph, shape_batch_count, vertex_position_count)
    j3d.vtx1.pack(stream, model.position_array, model.normal_array, model.color_arrays, model.texcoord_arrays)
    j3d.evp1.pack(stream, model.influence_groups, model.inverse_bind_matrices)
    j3d.drw1.pack(stream, model.matrix_descriptors)
    j3d.jnt1.pack(stream, model.joints)
    j3d.shp1.pack(stream, model.shapes)
    j3d.mat3.pack(stream, model.materials, model.subversion)
    if file_type == b'bdl4':
        j3d.mdl3.pack(stream, model.materials, model.textures)
    j3d.tex1.pack(stream, model.textures)

    header.file_size = stream.tell()
    stream.seek(0)
    Header.pack(stream, header)


def unpack(stream):
    header = Header.unpack(stream)
    scene_graph, shape_batch_count, vertex_position_count = j3d.inf1.unpack(stream)
    position_array, normal_array, color_arrays, texcoord_arrays = j3d.vtx1.unpack(stream)
    influence_groups, inverse_bind_matrices = j3d.evp1.unpack(stream)
    matrix_descriptors = j3d.drw1.unpack(stream)
    joints = j3d.jnt1.unpack(stream)
    shapes = j3d.shp1.unpack(stream)
    materials = j3d.mat3.unpack(stream, header.subversion)
    if header.file_type == b'bdl4':
        skip_section(stream, b'MDL3')
    textures = j3d.tex1.unpack(stream)

    position_array = position_array[0:vertex_position_count]

    if shape_batch_count != sum(len(shape.batches) for shape in shapes):
        raise FormatError('wrong number of shape batches')

    model = Model()
    model.file_type = header.file_type
    model.subversion = header.subversion
    model.scene_graph = scene_graph
    model.position_array = position_array
    model.normal_array = normal_array
    model.color_arrays = color_arrays
    model.texcoord_arrays = texcoord_arrays
    model.influence_groups = influence_groups
    model.inverse_bind_matrices = inverse_bind_matrices
    model.matrix_descriptors = matrix_descriptors
    model.joints = joints
    model.shapes = shapes
    model.materials = materials
    model.textures = textures

    return model

