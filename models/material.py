from collections import OrderedDict
import logging
import numpy
from OpenGL.GL import *
import gl
import gx
import j3d.material_archive
from modelview.path import PATH_BUILDER as _p
from modelview.object_model import (
    ValueChangedEvent,
    ReferenceAttribute,
    ReferenceList
)
from modelview.wrapper_model import (
    WrapperModel,
    wrapper_attribute as _attribute,
    wrapper_list as _list
)
import models.texture
import models.vertex_shader
import models.fragment_shader


logger = logging.getLogger(__name__)


MATRIX_BLOCK_BINDING_POINT = 0
MATERIAL_BLOCK_BINDING_POINT = 1
MATRIX_TABLE_TEXTURE_UNIT = 0
TEXTURE_UNITS = [1,2,3,4,5,6,7,8]


class LazyProperty:

    def __init__(self, fget):
        self.fget = fget

    def __get__(self, instance, owner=None):
        value = self.fget(instance)
        setattr(instance, self.fget.__name__, value)
        return value


class UseLightProxy(WrapperModel):

    def __getitem__(self, index):
        return bool(self.wrapped_object.light_mask & (1 << index))

    def __setitem__(self, index, value):
        current_value = self[index]
        if value == current_value:
            return
        if value:
            self.wrapped_object.light_mask |= (1 << index)
        else:
            self.wrapped_object.light_mask &= ~(1 << index)
        self.handle_event(ValueChangedEvent(), +_p[index])


class LightingMode(WrapperModel):
    material_source = _attribute()
    ambient_source = _attribute()
    diffuse_function = _attribute()
    attenuation_function = _attribute()
    light_enable = _attribute()
    use_light = _attribute(UseLightProxy, source_path=+_p)


class Channel(WrapperModel):
    color_mode = _attribute(LightingMode)
    alpha_mode = _attribute(LightingMode)
    material_color = _attribute()
    ambient_color = _attribute()


class TexCoordGenerator(WrapperModel):
    function = _attribute()
    source = _attribute()
    matrix = _attribute()


class TextureMatrix(WrapperModel):
    shape = _attribute()
    matrix_type = _attribute()
    center_s = _attribute()
    center_t = _attribute()
    unknown0 = _attribute()
    scale_s = _attribute()
    scale_t = _attribute()
    rotation = _attribute()
    translation_s = _attribute()
    translation_t = _attribute()
    projection_matrix = _attribute()

    def create_matrix(self):
        return self.wrapped_object.create_matrix()


class TevMode(WrapperModel):
    a = _attribute()
    b = _attribute()
    c = _attribute()
    d = _attribute()
    function = _attribute()
    bias = _attribute()
    scale = _attribute()
    clamp = _attribute()
    output = _attribute()


class TevStage(WrapperModel):
    texcoord = _attribute()
    texture = _attribute()
    color = _attribute()
    color_mode = _attribute(TevMode)
    alpha_mode = _attribute(TevMode)
    constant_color = _attribute()
    constant_alpha = _attribute()
    color_swap_table = _attribute()
    texture_swap_table = _attribute()
    indirect_stage = _attribute()
    indirect_format = _attribute()
    indirect_bias_components = _attribute()
    indirect_matrix = _attribute()
    wrap_s = _attribute()
    wrap_t = _attribute()
    add_previous_texcoord = _attribute()
    use_original_lod = _attribute()
    bump_alpha = _attribute()
    unknown0 = _attribute()
    unknown1 = _attribute()


class SwapTable(WrapperModel):
    r = _attribute()
    g = _attribute()
    b = _attribute()
    a = _attribute()


class IndirectStage(WrapperModel):
    texcoord = _attribute()
    texture = _attribute()
    scale_s = _attribute()
    scale_t = _attribute()


class IndirectMatrix(WrapperModel):
    significand_matrix = _attribute()
    scale_exponent = _attribute()


class AlphaTest(WrapperModel):
    function0 = _attribute()
    reference0 = _attribute()
    function1 = _attribute()
    reference1 = _attribute()
    operator = _attribute()


class DepthMode(WrapperModel):
    enable = _attribute()
    function = _attribute()
    update_enable = _attribute()


class BlendMode(WrapperModel):
    function = _attribute()
    source_factor = _attribute()
    destination_factor = _attribute()
    logical_operation = _attribute()


class ColorBlockProperty:

    def __init__(self, path, field_name):
        self.path = path
        self.field_name = field_name
        self.field_type = gl.vec4
        self.triggers = [path]

    def update_block(self, block, material):
        value = self.path.get_value(material)
        field = block[self.field_name]
        field[0] = value.r/255
        field[1] = value.g/255
        field[2] = value.b/255
        field[3] = value.a/255


class TextureMatrixBlockProperty:

    def __init__(self, path, field_name):
        self.path = path
        self.field_name = field_name
        self.field_type = gl.mat4x3
        self.triggers = [
            path + _p.shape,
            path + _p.matrix_type,
            path + _p.center_s,
            path + _p.center_t,
            path + _p.scale_s,
            path + _p.scale_t,
            path + _p.rotation,
            path + _p.translation_s,
            path + _p.translation_t,
            path + _p.projection_matrix
        ]

    def update_block(self, block, material):
        value = self.path.get_value(material).create_matrix()
        block[self.field_name][:value.shape[0], :] = value


class IndirectMatrixBlockProperty:

    def __init__(self, path, field_name):
        self.path = path
        self.field_name = field_name
        self.field_type = gl.mat3x2
        self.triggers = [
            +_p.significand_matrix,
            +_p.scale_exponent
        ]

    def update_block(self, block, material):
        matrix = self.path.get_value(material)
        value = numpy.zeros((2, 4),numpy.float32) #FIXME
        value[:, 0:3] = numpy.array(matrix.significand_matrix, numpy.float32)*2**matrix.scale_exponent
        block[self.field_name] = value


class BlockInfo:

    def __init__(self):
        self.properties = tuple(self._properties())

        self.block_type = gl.uniform_block('MaterialBlock', (
            (block_property.field_name, block_property.field_type)
            for block_property in self.properties
        ))

        self.trigger_table = {
            trigger : block_property
            for block_property in self.properties
            for trigger in block_property.triggers
        }

    @staticmethod
    def _properties():
        for i in range(2):
            yield ColorBlockProperty(+_p.channels[i].material_color, f'material_color{i}')
            yield ColorBlockProperty(+_p.channels[i].ambient_color, f'ambient_color{i}')

        yield ColorBlockProperty(+_p.tev_color_previous, 'tev_color_previous')
        for i in range(3):
            yield ColorBlockProperty(+_p.tev_colors[i], f'tev_color{i}')

        for i in range(4):
            yield ColorBlockProperty(+_p.kcolors[i], f'kcolor{i}')

        for i in range(10):
            yield TextureMatrixBlockProperty(+_p.texture_matrices[i], f'texture_matrix{i}')

        for i in range(3):
            yield IndirectMatrixBlockProperty(+_p.indirect_matrices[i], f'indmatrix{i}')


class ShaderInfo:

    def __init__(self):
        self.triggers = frozenset(self._triggers())

    @staticmethod
    def _triggers():
        yield +_p.channel_count
        for i in range(2):
            yield from ShaderInfo._channel_triggers(+_p.channels[i])

        yield +_p.texcoord_generator_count
        for i in range(8):
            yield from ShaderInfo._texcoord_generator_triggers(+_p.texcoord_generators[i])
        
        for i in range(10):
            yield +_p.texture_matrices[i].matrix_type

        yield +_p.tev_stage_count
        for i in range(16):
            yield from ShaderInfo._tev_stage_triggers(+_p.tev_stages[i])

        for i in range(4):
            yield from ShaderInfo._swap_table_triggers(+_p.swap_tables[i])

        yield +_p.indirect_stage_count
        for i in range(4):
            yield from ShaderInfo._indirect_stage_triggers(+_p.indirect_stages[i])

        for i in range(3):
            yield +_p.indirect_matrices[i].scale_exponent

        yield +_p.depth_test_early

        yield +_p.alpha_test.function0
        yield +_p.alpha_test.reference0
        yield +_p.alpha_test.function1
        yield +_p.alpha_test.reference1
        yield +_p.alpha_test.operator

    @staticmethod
    def _lighting_mode_triggers(path):
        yield path + _p.material_source
        yield path + _p.ambient_source
        yield path + _p.light_enable

    @staticmethod
    def _channel_triggers(path):
        yield from ShaderInfo._lighting_mode_triggers(path + _p.color_mode)
        yield from ShaderInfo._lighting_mode_triggers(path + _p.alpha_mode)

    @staticmethod
    def _texcoord_generator_triggers(path):
        yield path + _p.function
        yield path + _p.source
        yield path + _p.matrix

    @staticmethod
    def _tev_mode_triggers(path):
        yield path + _p.a
        yield path + _p.b
        yield path + _p.c
        yield path + _p.d
        yield path + _p.function
        yield path + _p.bias
        yield path + _p.scale
        yield path + _p.clamp
        yield path + _p.output

    @staticmethod
    def _tev_stage_triggers(path):
        yield path + _p.texcoord
        yield path + _p.texture
        yield path + _p.color
        yield from ShaderInfo._tev_mode_triggers(path + _p.color_mode)
        yield from ShaderInfo._tev_mode_triggers(path + _p.alpha_mode)
        yield path + _p.constant_color
        yield path + _p.constant_alpha
        yield path + _p.color_swap_table
        yield path + _p.texture_swap_table
        yield path + _p.indirect_stage
        yield path + _p.indirect_format
        yield path + _p.indirect_bias_components
        yield path + _p.indirect_matrix
        yield path + _p.wrap_s
        yield path + _p.wrap_t
        yield path + _p.add_previous_texcoord
        yield path + _p.use_original_lod
        yield path + _p.bump_alpha

    @staticmethod
    def _swap_table_triggers(path):
        yield path + _p.r
        yield path + _p.g
        yield path + _p.b
        yield path + _p.a

    @staticmethod
    def _indirect_stage_triggers(path):
        yield path + _p.texcoord
        yield path + _p.texture
        yield path + _p.scale_s
        yield path + _p.scale_t


class Material(WrapperModel):

    block_info = BlockInfo()
    shader_info = ShaderInfo()

    def __init__(self, wrapped_object):
        super().__init__(wrapped_object)
        self.gl_program_table = {}

    name = _attribute()
    unknown0 = _attribute()
    cull_mode = _attribute()

    channel_count = _attribute()
    channels = _attribute(_list(Channel))

    texcoord_generator_count = _attribute()
    texcoord_generators = _attribute(_list(TexCoordGenerator))
    texture_matrices = _attribute(_list(TextureMatrix))
    textures = ReferenceAttribute()

    tev_stage_count = _attribute()
    tev_stages = _attribute(_list(TevStage))
    tev_colors = _attribute(_list())
    tev_color_previous = _attribute()
    kcolors = _attribute(_list())
    swap_tables = _attribute(_list(SwapTable))

    indirect_stage_count = _attribute()
    indirect_stages = _attribute(_list(IndirectStage))
    indirect_matrices = _attribute(_list(IndirectMatrix))

    alpha_test = _attribute(AlphaTest)
    fog = _attribute()
    depth_test_early = _attribute()
    depth_mode = _attribute(DepthMode)
    blend_mode = _attribute(BlendMode)
    dither = _attribute()

    @property
    def enabled_channels(self):
        for i in range(self.channel_count):
            yield self.channels[i]

    @property
    def enabled_texcoord_generators(self):
        for i in range(self.texcoord_generator_count):
            yield self.texcoord_generators[i]

    @property
    def enabled_tev_stages(self):
        for i in range(self.tev_stage_count):
            yield self.tev_stages[i]

    @property
    def enabled_indirect_stages(self):
        for i in range(self.indirect_stage_count):
            yield self.indirect_stages[i]

    def handle_event(self, event, path):
        if isinstance(event, ValueChangedEvent):
            if path in self.block_info.trigger_table:
                block_property = self.block_info.trigger_table[path]
                block_property.update_block(self.gl_block, self)
            if path in self.shader_info.triggers:
                self.gl_shader_invalidate()
        super().handle_event(event, path)

    @LazyProperty
    def gl_block(self):
        block = self.gl_create_resource(self.block_info.block_type, GL_DYNAMIC_DRAW)
        for block_property in self.block_info.properties:
            block_property.update_block(block, self)
        return block

    def gl_program(self, transformation_type):
        if transformation_type in self.gl_program_table:
            return self.gl_program_table[transformation_type]

        vertex_shader_string = models.vertex_shader.create_shader_string(self, transformation_type)
        fragment_shader_string = models.fragment_shader.create_shader_string(self)
        vertex_shader = self.gl_create_resource(gl.Shader, GL_VERTEX_SHADER, vertex_shader_string)
        fragment_shader = self.gl_create_resource(gl.Shader, GL_FRAGMENT_SHADER, fragment_shader_string)
        program = self.gl_create_resource(gl.Program, vertex_shader, fragment_shader)
        self.gl_delete_resource(vertex_shader)
        self.gl_delete_resource(fragment_shader)

        glUseProgram(program)

        matrix_block_index = glGetUniformBlockIndex(program, b'MatrixBlock')
        glUniformBlockBinding(program, matrix_block_index, MATRIX_BLOCK_BINDING_POINT)

        material_block_index = glGetUniformBlockIndex(program, b'MaterialBlock')
        if material_block_index != GL_INVALID_INDEX:
            glUniformBlockBinding(program, material_block_index, MATERIAL_BLOCK_BINDING_POINT)

        program.matrix_index_location = glGetUniformLocation(program, 'matrix_index') #<-?

        matrix_table_location = glGetUniformLocation(program, 'matrix_table')
        if matrix_table_location != -1:
            glUniform1i(matrix_table_location, MATRIX_TABLE_TEXTURE_UNIT)

        for i in range(8):
            location = glGetUniformLocation(program, 'texmap{}'.format(i))
            if location == -1: continue
            glUniform1i(location, TEXTURE_UNITS[i])

        self.gl_program_table[transformation_type] = program
        return program

    def gl_shader_invalidate(self):
        for program in self.gl_program_table.values():
            self.gl_delete_resource(program)
        self.gl_program_table.clear()

    @property
    def gl_cull_mode(self):
        if self.cull_mode == gx.CULL_FRONT:
            return GL_FRONT
        if self.cull_mode == gx.CULL_BACK:
            return GL_BACK
        if self.cull_mode == gx.CULL_ALL:
            return GL_FRONT_AND_BACK
        raise ValueError('Invalid cull mode: {}'.format(self.cull_mode))

    @property
    def gl_depth_function(self):
        if self.depth_mode.function == gx.NEVER:
            return GL_NEVER
        if self.depth_mode.function == gx.LESS:
            return GL_LESS
        if self.depth_mode.function == gx.EQUAL:
            return GL_EQUAL
        if self.depth_mode.function == gx.LEQUAL:
            return GL_LEQUAL
        if self.depth_mode.function == gx.GREATER:
            return GL_GREATER
        if self.depth_mode.function == gx.NEQUAL:
            return GL_NOTEQUAL
        if self.depth_mode.function == gx.GEQUAL:
            return GL_GEQUAL
        if self.depth_mode.function == gx.ALWAYS:
            return GL_ALWAYS
        raise ValueError('Invalid compare function: {}'.format(self.depth_mode.function))

    @property
    def gl_blend_source_factor(self):
        if self.blend_mode.source_factor == gx.BL_ZERO:
            return GL_ZERO
        if self.blend_mode.source_factor == gx.BL_ONE:
            return GL_ONE
        if self.blend_mode.source_factor == gx.BL_SRCALPHA:
            return GL_SRC_ALPHA
        if self.blend_mode.source_factor == gx.BL_INVSRCALPHA:
            return GL_ONE_MINUS_SRC_ALPHA
        if self.blend_mode.source_factor == gx.BL_DSTALPHA:
            return GL_DST_ALPHA
        if self.blend_mode.source_factor == gx.BL_INVDSTALPHA:
            return GL_ONE_MINUS_DST_ALPHA
        if self.blend_mode.source_factor == gx.BL_DSTCLR:
            return GL_DST_COLOR
        if self.blend_mode.source_factor == gx.BL_INVDSTCLR:
            return GL_ONE_MINUS_DST_COLOR
        raise ValueError('Invalid blend source factor: {}'.format(self.blend_mode.source_factor))

    @property
    def gl_blend_destination_factor(self):
        if self.blend_mode.destination_factor == gx.BL_ZERO:
            return GL_ZERO
        if self.blend_mode.destination_factor == gx.BL_ONE:
            return GL_ONE
        if self.blend_mode.destination_factor == gx.BL_SRCALPHA:
            return GL_SRC_ALPHA
        if self.blend_mode.destination_factor == gx.BL_INVSRCALPHA:
            return GL_ONE_MINUS_SRC_ALPHA
        if self.blend_mode.destination_factor == gx.BL_DSTALPHA:
            return GL_DST_ALPHA
        if self.blend_mode.destination_factor == gx.BL_INVDSTALPHA:
            return GL_ONE_MINUS_DST_ALPHA
        if self.blend_mode.destination_factor == gx.BL_SRCCLR:
            return GL_SRC_COLOR
        if self.blend_mode.destination_factor == gx.BL_INVSRCCLR:
            return GL_ONE_MINUS_SRC_COLOR
        raise ValueError('Invalid blend destination factor: {}'.format(self.blend_mode.destination_factor))

    @property
    def gl_blend_logical_operation(self):
        if self.blend_mode.logical_operation == gx.LO_CLEAR:
            return GL_CLEAR
        if self.blend_mode.logical_operation == gx.LO_AND:
            return GL_AND
        if self.blend_mode.logical_operation == gx.LO_REVAND:
            return GL_AND_REVERSE
        if self.blend_mode.logical_operation == gx.LO_COPY:
            return GL_COPY
        if self.blend_mode.logical_operation == gx.LO_INVAND:
            return GL_AND_INVERTED
        if self.blend_mode.logical_operation == gx.LO_NOOP:
            return GL_NOOP
        if self.blend_mode.logical_operation == gx.LO_XOR:
            return GL_XOR
        if self.blend_mode.logical_operation == gx.LO_OR:
            return GL_OR
        if self.blend_mode.logical_operation == gx.LO_NOR:
            return GL_NOR
        if self.blend_mode.logical_operation == gx.LO_EQUIV:
            return GL_EQUIV
        if self.blend_mode.logical_operation == gx.LO_INV:
            return GL_INVERT
        if self.blend_mode.logical_operation == gx.LO_REVOR:
            return GL_OR_INVERTED
        if self.blend_mode.logical_operation == gx.LO_INVCOPY:
            return GL_COPY_INVERTED
        if self.blend_mode.logical_operation == gx.LO_INVOR:
            return GL_OR_INVERTED
        if self.blend_mode.logical_operation == gx.LO_INVNAND:
            return GL_NAND
        if self.blend_mode.logical_operation == gx.LO_SET:
            return GL_SET
        raise ValueError('Invalid logical operation: {}'.format(self.blend_mode.logical_operation))

    def gl_bind(self, shape):
        self.gl_block.bind(MATERIAL_BLOCK_BINDING_POINT)

        for i, texture in enumerate(self.textures):
            if texture is None:
                continue
            texture.gl_bind(TEXTURE_UNITS[i])

        if self.cull_mode != gx.CULL_NONE:
            glEnable(GL_CULL_FACE)
            glCullFace(self.gl_cull_mode)
        else:
            glDisable(GL_CULL_FACE)

        if self.depth_mode.enable:
            glEnable(GL_DEPTH_TEST)
            glDepthFunc(self.gl_depth_function)
            glDepthMask(self.depth_mode.update_enable)
        else:
            glDisable(GL_DEPTH_TEST)

        if self.blend_mode.function == gx.BM_BLEND:
            glEnable(GL_BLEND)
            glBlendEquation(GL_FUNC_ADD)
            glBlendFunc(self.gl_blend_source_factor, self.gl_blend_destination_factor)
        elif self.blend_mode.function == gx.BM_SUBTRACT:
            glEnable(GL_BLEND)
            glBlendEquation(GL_FUNC_REVERSE_SUBTRACT)
            glBlendFunc(GL_ONE, GL_ONE)
        else:
            glDisable(GL_BLEND)

        if self.blend_mode.function == gx.BM_LOGIC:
            glEnable(GL_COLOR_LOGIC_OP)
            glLogicOp(self.gl_blend_logical_operation)
        else:
            glDisable(GL_COLOR_LOGIC_OP)

        if self.dither:
            glEnable(GL_DITHER)
        else:
            glDisable(GL_DITHER)

        program = self.gl_program(shape.transformation_type)

        glUseProgram(program)

        if shape.transformation_type == 0:
            glUniform1i(program.matrix_index_location, shape.batches[0].matrix_table[0])

    def gl_delete(self):
        super().gl_delete()
        try:
            del self.gl_block
        except AttributeError:
            pass
        self.gl_program_table.clear()


class MaterialArchive:

    def __init__(self, materials, textures=None):
        if textures is None:
            # Remove duplicates but keep the order
            textures = list(OrderedDict.fromkeys(
                texture
                for material in materials
                for texture in material.textures
                if texture is not None
            ))
        self.materials = materials
        self.textures = textures

    @staticmethod
    def load(file_path):
        with open(file_path, 'rb') as stream:
            material_archive = j3d.material_archive.unpack(stream)
        materials = list(map(Material, material_archive.materials))
        textures = list(map(models.texture.Texture, material_archive.textures))
        material_archive = MaterialArchive(materials, textures)
        material_archive.init_references()
        return material_archive

    def save(self, file_path):
        self.sync_reference_indices()
        materials = [material.viewed_object for material in self.materials]
        textures = [texture.viewed_object for texture in self.textures]
        material_archive = j3d.material_archive.MaterialArchive(materials, textures)
        with open(file_path, 'wb') as stream:
            j3d.material_archive.pack(stream, material_archive)

    def init_references(self):
        """Initialize references.

        Initialize references into the texture list.
        """
        for material in self.materials:
            material.textures = ReferenceList(
                self.textures[texture_index] if texture_index is not None else None
                for texture_index in material.wrapped_object.texture_indices
            )

    def sync_reference_indices(self):
        """Synchronize reference indices.

        Indices used to reference into the texture list are not automatically
        kept in sync. This method needs to be manually called to synchronize the
        reference indices.
        """
        for material in self.materials:
            for i, texture in enumerate(material.textures):
                texture_index = None
                if texture is not None:
                    texture_index = self.textures.index(texture)
                material.wrapped_object.texture_indices[i] = texture_index

