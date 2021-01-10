import copy
import numpy
from OpenGL.GL import *
import gl
import gx
from j3d.inf1 import NodeType
from j3d.drw1 import MatrixType
import j3d.model
import views
import views.shape
import views.material
import views.texture
import views.vertex_shader


class ResourceInUseError(Exception):
    pass


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

        glEnableVertexAttribArray(views.vertex_shader.MATRIX_INDEX_ATTRIBUTE_LOCATION)
        vertex_type = vertex_array.dtype
        stride = vertex_type.itemsize
        offset = vertex_type.fields[gx.VA_PTNMTXIDX.name][1]
        glVertexAttribIPointer(views.vertex_shader.MATRIX_INDEX_ATTRIBUTE_LOCATION,1,GL_UNSIGNED_INT,stride,GLvoidp(offset))


class GLDirectArray:

    def __init__(self, attribute):
        self.attribute = attribute

    def field(self):
        return (self.attribute.name, numpy.uint32)

    def load(self, shape, vertex_array):
        vertex_array[self.attribute.name] = numpy.concatenate([primitive.vertices[self.attribute.name] for primitive in shape.primitives])


class GLArray(numpy.ndarray):

    def field(self):
        return (self.attribute.name,self.dtype,self.shape[1])

    def load(self,shape,vertex_array):
        index_array = numpy.concatenate([primitive.vertices[self.attribute.name] for primitive in shape.primitives])
        numpy.take(self,index_array,0,vertex_array[self.attribute.name])
        location = views.vertex_shader.ATTRIBUTE_LOCATION_TABLE[self.attribute]
        glEnableVertexAttribArray(location)
        vertex_type = vertex_array.dtype
        stride = vertex_type.itemsize
        offset = vertex_type.fields[self.attribute.name][1]
        glVertexAttribPointer(location,self.component_count,self.component_type,self.normalize,stride,GLvoidp(offset))


def gl_convert_array(source):
    if source is None:
        return None

    destination = numpy.asfarray(source,numpy.float32)

    if source.component_type != gx.F32 and source.scale_exponent != 0:
        destination *= 2**(-source.scale_exponent)

    destination = destination.view(GLArray)
    destination.attribute = source.attribute
    destination.component_type = GL_FLOAT
    destination.component_count = source.shape[1]
    destination.normalize = False
    return destination


def gl_convert_color_array(source):
    if source is None:
        return None

    if source.component_type in {gx.RGB8,gx.RGBX8,gx.RGBA8}:
        destination = source
    
    if source.component_type == gx.RGB565:
        destination = numpy.empty((element_count,4),numpy.uint8)
        destination[:,0] = ((source >> 8) & 0xF8) | ((source >> 13) & 0x7)
        destination[:,1] = ((source >> 3) & 0xFC) | ((source >> 9) & 0x3)
        destination[:,2] = ((source << 3) & 0xF8) | ((source >> 2) & 0x7)
        destination[:,3] = 0xFF

    if source.component_type == gx.RGBA4:
        destination = numpy.empty((element_count,4),numpy.uint8)
        destination[:,0] = ((source >> 8) & 0xF0) | ((source >> 12) & 0xF)
        destination[:,1] = ((source >> 4) & 0xF0) | ((source >> 8) & 0xF)
        destination[:,2] = (source & 0xF0) | ((source >> 4) & 0xF)
        destination[:,3] = ((source << 4) & 0xF0) | (source & 0xF)

    if source.component_type == gx.RGBA6:
        destination = numpy.empty((element_count,4),numpy.uint8)
        destination[:,0] = ((source >> 16) & 0xFC) | ((source >> 22) & 0x3)
        destination[:,1] = ((source >> 10) & 0xFC) | ((source >> 16) & 0x3)
        destination[:,2] = ((source >> 4) & 0xFC) | ((source >> 10) & 0x3)
        destination[:,3] = ((source << 2) & 0xFC) | ((source >> 4) & 0x3)

    has_alpha = source.component_count == gx.CLR_RGBA and source.component_type in {gx.RGBA8, gx.RGBA4, gx.RGBA6}

    destination = destination.view(GLArray)
    destination.attribute = source.attribute
    destination.component_type = GL_UNSIGNED_BYTE
    destination.component_count = 4 if has_alpha else 3
    destination.normalize = True
    return destination


class SceneGraphNode(views.View):
    node_type = views.ReadOnlyAttribute()
    index = views.Attribute()
    # We have to use a lambda as SceneGraphNode does not yet exist
    children = views.ViewAttribute(views.ViewListView, lambda *args: SceneGraphNode(*args))


class SceneGraph(views.View):
    unknown0 = views.ReadOnlyAttribute()
    children = views.ViewAttribute(views.ViewListView, SceneGraphNode)


class Model(views.View):

    def __init__(self, viewed_object):
        super().__init__(viewed_object)
        self.file_path = None

    file_type = views.Attribute()
    subversion = views.ReadOnlyAttribute()
    scene_graph = views.ViewAttribute(SceneGraph)
    position_array = views.ReadOnlyAttribute()
    normal_array = views.ReadOnlyAttribute()
    color_arrays = views.ReadOnlyAttribute()
    texcoord_arrays = views.ReadOnlyAttribute()
    influence_groups = views.ReadOnlyAttribute()
    inverse_bind_matrices = views.ReadOnlyAttribute()
    matrix_definitions = views.ReadOnlyAttribute()
    joints = views.ReadOnlyAttribute()
    shapes = views.ViewAttribute(views.ViewListView, views.shape.Shape)
    materials = views.ViewAttribute(views.ViewListView, views.material.Material)
    textures = views.ViewAttribute(views.ViewListView, views.texture.Texture)

    def gl_init(self):
        array_table = {}
        array_table[gx.VA_PTNMTXIDX] = GLMatrixIndexArray()
        array_table.update({attribute : GLDirectArray(attribute) for attribute in gx.VA_TEXMTXIDX})
        array_table[gx.VA_POS] = gl_convert_array(self.position_array)
        array_table[gx.VA_NRM] = gl_convert_array(self.normal_array)
        array_table.update({attribute : gl_convert_color_array(array) for attribute, array in zip(gx.VA_CLR, self.color_arrays)})
        array_table.update({attribute : gl_convert_array(array) for attribute, array in zip(gx.VA_TEX, self.texcoord_arrays)})

        for shape in self.shapes:
            shape.gl_init(array_table)

        self.gl_joints = [copy.copy(joint) for joint in self.joints]
        self.gl_joint_matrices = numpy.empty((len(self.joints),3,4),numpy.float32)
        self.gl_matrix_table = self.gl_create_resource(gl.TextureBuffer, GL_DYNAMIC_DRAW,GL_RGBA32F,(len(self.matrix_definitions),3,4),numpy.float32)
        self.gl_update_matrix_table()

    def gl_update_joint_matrices(self,node,parent_joint=None,parent_joint_matrix=numpy.eye(3,4,dtype=numpy.float32)):
        for child in node.children:
            if child.node_type == NodeType.JOINT:
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

        for matrix,matrix_definition in zip(self.gl_matrix_table,self.matrix_definitions):
            if matrix_definition.matrix_type == MatrixType.JOINT:
                matrix[:] = self.gl_joint_matrices[matrix_definition.index]
            elif matrix_definition.matrix_type == MatrixType.INFLUENCE_GROUP:
                influence_group = self.influence_groups[matrix_definition.index]
                matrix[:] = sum(influence.weight*influence_matrices[influence.index] for influence in influence_group)
            else:
                ValueError('invalid matrix type')

    def gl_draw_shape(self, material, shape):
        if shape.gl_hide: return
        material.gl_bind(shape, self.textures)
        shape.gl_bind()
        shape.gl_draw()

    def gl_draw_node(self, node, parent_material=None):
        for child in node.children:
            if child.node_type == NodeType.SHAPE:
                if parent_material.unknown0 == 1:
                    self.gl_draw_shape(parent_material, self.shapes[child.index])
                self.gl_draw_node(child, parent_material)
                if parent_material.unknown0 == 4:
                    self.gl_draw_shape(parent_material, self.shapes[child.index])
            elif child.node_type == NodeType.MATERIAL:
                self.gl_draw_node(child, self.materials[child.index])
            else:
                self.gl_draw_node(child, parent_material)

    def gl_draw(self):
        self.gl_matrix_table.bind_texture(views.material.MATRIX_TABLE_TEXTURE_UNIT)
        self.gl_draw_node(self.scene_graph)

    @staticmethod
    def load(file_path):
        with open(file_path, 'rb') as stream:
            model = j3d.model.unpack(stream)
        model = Model(model)
        model.file_path = file_path
        return model

    def save(self, file_path):
        self.file_path = file_path
        with open(file_path, 'wb') as stream:
            j3d.model.pack(stream, self.viewed_object)

    def get_materials_using_texture(self, texture_index):
        """Get materials that use a given texture.

        :param texture_index: Index of the texture in the texture list.
        :return: List of the materials that use the texture.
        """
        materials = []
        for material in self.materials:
            if texture_index in material.texture_indices:
                materials.append(material)
                continue
        return materials

    def insert_texture(self, index, texture):
        """Insert texture in the texture list.

        :param index: Index to insert the texture at.
        :param texture: Texture to insert.
        """
        self.textures.insert(index, texture)
        for material in self.materials:
            for i, ti in enumerate(material.texture_indices):
                if ti is not None and ti >= index:
                    material.texture_indices[i] += 1

    def remove_texture(self, index):
        """Remove texture from the texture list.

        :param index: Index of texture to remove.
        :raise ResourceInUseError: Raised if the texture is being used.
        """
        if self.get_materials_using_texture(index):
            raise ResourceInUseError('Cannot remove texture in use')
        # Texture indices are adjusted before the texture is removed to ensure
        # that the texture indices are never invalid
        for material in self.materials:
            for i, ti in enumerate(material.texture_indices):
                if ti is not None and ti > index:
                    material.texture_indices[i] -= 1
        del self.textures[index]

    def move_texture(self, from_index, to_index):
        """Move texture to a new position in the texture list.

        :param from_index: Index of the texture before the move.
        :param to_index: Index of the texture after the move.
        """
        # The move is done by inserting the texture at the new position,
        # changing texture indices from the old position to the new position,
        # and then removing the texture from the old position. This ensures that
        # there will be no invalid texture indices at any point.
        if from_index < to_index:
            insert_index = to_index + 1
            remove_index = from_index
        else:
            insert_index = to_index
            remove_index = from_index + 1
        texture = self.textures[from_index]
        self.insert_texture(insert_index, texture)
        assert self.textures[remove_index] is texture
        for material in self.materials:
            for i, ti in enumerate(material.texture_indices):
                if ti == remove_index:
                    material.texture_indices[i] = insert_index
        self.remove_texture(remove_index)
        assert self.textures[to_index] is texture

