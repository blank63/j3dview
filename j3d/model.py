import functools
import copy
import numpy
from OpenGL.GL import *
from btypes.big_endian import *
import gl
import gx
import gx.texture
import j3d.inf1
import j3d.vtx1
import j3d.evp1
import j3d.drw1
import j3d.jnt1
import j3d.shp1
import j3d.mat3
import j3d.mdl3
import j3d.tex1
from j3d.opengl import *
import j3d.vertex_shader
import j3d.fragment_shader


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
    def pack(cls,stream,header):
        if header.file_type == b'bmd3':
            header.section_count = 8
        elif header.file_type == b'bdl4':
            header.section_count = 9
        else:
            raise ValueError('invalid file type')

        super().pack(stream,header)

    @classmethod
    def unpack(cls,stream):
        header = super().unpack(stream)

        if header.magic != b'J3D2':
            raise FormatError('invalid magic')

        if header.file_type == b'bmd3':
            valid_section_count = 8
            valid_subversions = {b'SVR3',b'\xFF\xFF\xFF\xFF'}
        elif header.file_type == b'bdl4':
            valid_section_count = 9
            valid_subversions = {b'SVR3'}
        else:
            raise FormatError('invalid file type')

        if header.section_count != valid_section_count:
            raise FormatError('invalid section count')

        if header.subversion not in valid_subversions:
            raise FormatError('invalid subversion')

        return header


def matrix3x4_array_multiply(a,b):
    c = numpy.empty(a.shape,numpy.float32)
    numpy.einsum('ijk,ikl->ijl',a[:,:,:3],b[:,:,:3],out=c[:,:,:3])
    numpy.einsum('ijk,ik->ij',a[:,:,:3],b[:,:,3],out=c[:,:,3])
    c[:,:,3] += a[:,:,3]
    return c


class GLMatrixIndexArray:

    @staticmethod
    def field():
        return (gx.VA_PTNMTXIDX.name,numpy.uint32)

    @staticmethod
    def load(shape,vertex_array):
        destination = vertex_array[gx.VA_PTNMTXIDX.name]
        vertex_index = 0
        matrix_table = numpy.zeros(10,numpy.uint32)

        for batch in shape.batches:
            source = numpy.concatenate([primitive.vertices[gx.VA_PTNMTXIDX.name] for primitive in batch.primitives])
            source //= 3

            for i,index in enumerate(batch.matrix_table):
                if index == 0xFFFF: continue
                matrix_table[i] = index

            length = sum(len(primitive.vertices) for primitive in batch.primitives)
            numpy.take(matrix_table,source,0,destination[vertex_index:vertex_index + length])
            vertex_index += length

        glEnableVertexAttribArray(MATRIX_INDEX_ATTRIBUTE_LOCATION)
        vertex_type = vertex_array.dtype
        stride = vertex_type.itemsize
        offset = vertex_type.fields[gx.VA_PTNMTXIDX.name][1]
        glVertexAttribIPointer(MATRIX_INDEX_ATTRIBUTE_LOCATION,1,GL_UNSIGNED_INT,stride,GLvoidp(offset))


class GLProgram(gl.Program):

    def __init__(self,vertex_shader,fragment_shader):
        super().__init__(vertex_shader,fragment_shader)

        glUseProgram(self)

        matrix_block_index = glGetUniformBlockIndex(self,b'MatrixBlock')
        glUniformBlockBinding(self,matrix_block_index,MATRIX_BLOCK_BINDING_POINT)

        material_block_index = glGetUniformBlockIndex(self,b'MaterialBlock')
        if material_block_index != GL_INVALID_INDEX:
            glUniformBlockBinding(self,material_block_index,MATERIAL_BLOCK_BINDING_POINT)

        matrix_table_location = glGetUniformLocation(self,'matrix_table')
        if matrix_table_location != -1:
            glUniform1i(matrix_table_location,MATRIX_TABLE_TEXTURE_UNIT)

        for i in range(8):
            location = glGetUniformLocation(self,'texmap{}'.format(i))
            if location == -1: continue
            glUniform1i(location,TEXTURE_UNITS[i])


class GLDrawObject:

    def __init__(self,shape,material,program):
        self.shape = shape
        self.material = material
        self.program = program

    @property
    def hide(self):
        return self.shape.gl_hide

    def bind(self,textures):
        self.material.gl_bind(textures)
        glUseProgram(self.program)
        self.shape.gl_bind()

    def draw(self):
        self.shape.gl_draw()


class Model:

    def gl_init(self):
        self.gl_vertex_shader_factory = functools.lru_cache(maxsize=None)(functools.partial(gl.Shader,GL_VERTEX_SHADER))
        self.gl_fragment_shader_factory = functools.lru_cache(maxsize=None)(functools.partial(gl.Shader,GL_FRAGMENT_SHADER))
        self.gl_program_factory = functools.lru_cache(maxsize=None)(GLProgram)
        self.gl_texture_factory = functools.lru_cache(maxsize=None)(gx.texture.GLTexture)

        array_table = {gx.VA_PTNMTXIDX:GLMatrixIndexArray()}
        array_table.update((attribute,array.gl_convert()) for attribute,array in self.array_table.items())

        for shape in self.shapes:
            shape.gl_init(array_table)

        for material in self.materials:
            material.gl_init()

        for texture in self.textures:
            texture.gl_init(self.gl_texture_factory)

        self.gl_joints = [copy.copy(joint) for joint in self.joints]
        self.gl_joint_matrices = numpy.empty((len(self.joints),3,4),numpy.float32)
        self.gl_matrix_table = gl.TextureBuffer(GL_DYNAMIC_DRAW,GL_RGBA32F,(len(self.matrix_descriptors),3,4),numpy.float32)
        self.gl_update_matrix_table()

        self.gl_draw_objects = list(self.gl_generate_draw_objects(self.scene_graph))
        self.gl_draw_objects.sort(key=lambda draw_object: draw_object.material.unknown0)

    def gl_create_draw_object(self,shape,material):
        vertex_shader = self.gl_vertex_shader_factory(j3d.vertex_shader.create_shader_string(material,shape))
        fragment_shader = self.gl_fragment_shader_factory(j3d.fragment_shader.create_shader_string(material))
        program = self.gl_program_factory(vertex_shader,fragment_shader)
        return GLDrawObject(shape,material,program)

    def gl_generate_draw_objects(self,node,parent_material=None):
        for child in node.children:
            if child.node_type == j3d.inf1.NodeType.SHAPE:
                yield self.gl_create_draw_object(self.shapes[child.index],parent_material)
                yield from self.gl_generate_draw_objects(child,parent_material)
            elif child.node_type == j3d.inf1.NodeType.MATERIAL:
                yield from self.gl_generate_draw_objects(child,self.materials[child.index])
            else:
                yield from self.gl_generate_draw_objects(child,parent_material)

    def gl_update_joint_matrices(self,node,parent_joint=None,parent_joint_matrix=numpy.eye(3,4,dtype=numpy.float32)):
        for child in node.children:
            if child.node_type == j3d.inf1.NodeType.JOINT:
                joint = self.gl_joints[child.index]
                joint_matrix = self.gl_joint_matrices[child.index]
                joint_matrix[:] = joint.create_matrix(parent_joint,parent_joint_matrix)
                self.gl_update_joint_matrices(child,joint,joint_matrix)
            else:
                self.gl_update_joint_matrices(child,parent_joint,parent_joint_matrix)

    def gl_update_matrix_table(self):
        self.gl_update_joint_matrices(self.scene_graph)

        if self.inverse_bind_matrices is not None:
            influence_matrices = matrix3x4_array_multiply(self.gl_joint_matrices,self.inverse_bind_matrices)

        for matrix,matrix_descriptor in zip(self.gl_matrix_table,self.matrix_descriptors):
            if matrix_descriptor.matrix_type == j3d.drw1.MatrixType.JOINT:
                matrix[:] = self.gl_joint_matrices[matrix_descriptor.index]
            elif matrix_descriptor.matrix_type == j3d.drw1.MatrixType.INFLUENCE_GROUP:
                influence_group = self.influence_groups[matrix_descriptor.index]
                matrix[:] = sum(influence.weight*influence_matrices[influence.index] for influence in influence_group)
            else:
                ValueError('invalid matrix type')

    def gl_draw(self):
        self.gl_matrix_table.bind_texture(MATRIX_TABLE_TEXTURE_UNIT)

        for draw_object in self.gl_draw_objects:
            if draw_object.hide: continue
            draw_object.bind(self.textures)
            draw_object.draw()


def skip_section(stream,magic):
    if stream.read(4) != magic:
        raise FormatError('invalid magic')
    section_size = uint32.unpack(stream)
    stream.seek(section_size - 8,SEEK_CUR)


def pack(stream,model,file_type=None):
    if file_type is None:
        file_type = model.file_type
    elif file_type in {'bmd','.bmd'}:
        file_type = b'bmd3'
    elif file_type in {'bdl','.bdl'}:
        file_type = b'bdl4'

    header = Header()
    header.file_type = file_type
    header.subversion = model.subversion
    stream.write(b'\x00'*Header.sizeof())

    shape_batch_count = sum(len(shape.batches) for shape in model.shapes)
    vertex_position_count = len(model.array_table[gx.VA_POS])

    j3d.inf1.pack(stream,model.scene_graph,shape_batch_count,vertex_position_count)
    j3d.vtx1.pack(stream,model.array_table)
    j3d.evp1.pack(stream,model.influence_groups,model.inverse_bind_matrices)
    j3d.drw1.pack(stream,model.matrix_descriptors)
    j3d.jnt1.pack(stream,model.joints)
    j3d.shp1.pack(stream,model.shapes)
    j3d.mat3.pack(stream,model.materials,model.subversion)
    if file_type == b'bdl4':
        j3d.mdl3.pack(stream,model.materials,model.textures)
    j3d.tex1.pack(stream,model.textures)

    header.file_size = stream.tell()
    stream.seek(0)
    Header.pack(stream,header)


def unpack(stream):
    header = Header.unpack(stream)
    scene_graph,shape_batch_count,vertex_position_count = j3d.inf1.unpack(stream)
    array_table = j3d.vtx1.unpack(stream)
    influence_groups,inverse_bind_matrices = j3d.evp1.unpack(stream)
    matrix_descriptors = j3d.drw1.unpack(stream)
    joints = j3d.jnt1.unpack(stream)
    shapes = j3d.shp1.unpack(stream)
    materials = j3d.mat3.unpack(stream,header.subversion)
    if header.file_type == b'bdl4':
        skip_section(stream,b'MDL3')
    textures = j3d.tex1.unpack(stream)

    array_table[gx.VA_POS] = array_table[gx.VA_POS][0:vertex_position_count]

    if shape_batch_count != sum(len(shape.batches) for shape in shapes):
        raise FormatError('wrong number of shape batches')

    model = Model()
    model.file_type = header.file_type
    model.subversion = header.subversion
    model.scene_graph = scene_graph
    model.array_table = array_table
    model.influence_groups = influence_groups
    model.inverse_bind_matrices = inverse_bind_matrices
    model.matrix_descriptors = matrix_descriptors
    model.joints = joints
    model.shapes = shapes
    model.materials = materials
    model.textures = textures

    return model

