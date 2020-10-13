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
            raise FormatError(f'invalid magic: {header.magic}')
        if header.file_type not in {b'bmd3', b'bdl4'}:
            raise FormatError(f'invalid file type: {header.file_type}')
        if header.subversion not in {b'\xFF\xFF\xFF\xFF', b'SVR3'}:
            logger.warning(f'unexpected subversion: %s', header.subversion)
        return header


class Model:
    pass


def get_section_count(file_type):
    if file_type == b'bmd3':
        return 8
    if file_type == b'bdl4':
        return 9
    raise ValueError(f'invalid file type: {file_type}')


def skip_section(stream, magic):
    if stream.read(4) != magic:
        raise FormatError(f'invalid magic: {magic}')
    section_size = uint32.unpack(stream)
    stream.seek(section_size - 8, SEEK_CUR)


def pack(stream, model):
    header = Header()
    header.file_type = model.file_type
    header.section_count = get_section_count(model.file_type)
    header.subversion = model.subversion
    stream.write(b'\x00'*Header.sizeof())

    shape_batch_count = sum(len(shape.batches) for shape in model.shapes)
    vertex_position_count = len(model.position_array)

    j3d.inf1.pack(stream, model.scene_graph, shape_batch_count, vertex_position_count)
    j3d.vtx1.pack(stream, model.position_array, model.normal_array, model.color_arrays, model.texcoord_arrays)
    j3d.evp1.pack(stream, model.influence_groups, model.inverse_bind_matrices)
    j3d.drw1.pack(stream, model.matrix_definitions)
    j3d.jnt1.pack(stream, model.joints)
    j3d.shp1.pack(stream, model.shapes)
    j3d.mat3.pack(stream, model.materials, model.subversion)
    if model.file_type == b'bdl4':
        j3d.mdl3.pack(stream, model.materials, model.textures)
    j3d.tex1.pack(stream, model.textures)

    header.file_size = stream.tell()
    stream.seek(0)
    Header.pack(stream, header)


def unpack(stream):
    header = Header.unpack(stream)
    if header.section_count != get_section_count(header.file_type):
        raise FormatError(f'invalid section count: {header.section_count}')

    inf1 = j3d.inf1.unpack(stream)
    vtx1 = j3d.vtx1.unpack(stream)
    evp1 = j3d.evp1.unpack(stream)
    matrix_definitions = j3d.drw1.unpack(stream)
    joints = j3d.jnt1.unpack(stream)
    shapes = j3d.shp1.unpack(stream)
    materials = j3d.mat3.unpack(stream, header.subversion)
    if header.file_type == b'bdl4':
        skip_section(stream, b'MDL3')
    textures = j3d.tex1.unpack(stream)

    # The position array read from the VTX1 section might be longer than it
    # should be, due to the way the VTX1 arrays are read
    if inf1.vertex_position_count > len(vtx1.position_array):
        logger.warning('unexpected vertex_position_count value: %s', inf1.vertex_position_count)
    position_array = vtx1.position_array[:inf1.vertex_position_count]

    shape_batch_count = sum(len(shape.batches) for shape in shapes)
    if inf1.shape_batch_count != shape_batch_count:
        logger.warning('unexpected shape_batch_count value: %s', inf1.shape_batch_count)

    if evp1.inverse_bind_matrices is not None:
        if len(evp1.inverse_bind_matrices) != len(joints):
            raise FormatError('wrong number of inverse bind matrices')

    model = Model()
    model.file_type = header.file_type
    model.subversion = header.subversion
    model.scene_graph = inf1.scene_graph
    model.position_array = position_array
    model.normal_array = vtx1.normal_array
    model.color_arrays = vtx1.color_arrays
    model.texcoord_arrays = vtx1.texcoord_arrays
    model.influence_groups = evp1.influence_groups
    model.inverse_bind_matrices = evp1.inverse_bind_matrices
    model.matrix_definitions = matrix_definitions
    model.joints = joints
    model.shapes = shapes
    model.materials = materials
    model.textures = textures
    return model

