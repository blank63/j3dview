from math import cos,sin,radians
import numpy
from OpenGL.GL import *
import gl
import gx
import views
import views.vertex_shader
import views.fragment_shader

import logging
logger = logging.getLogger(__name__)


MATRIX_BLOCK_BINDING_POINT = 0
MATERIAL_BLOCK_BINDING_POINT = 1
MATRIX_TABLE_TEXTURE_UNIT = 0
TEXTURE_UNITS = [1,2,3,4,5,6,7,8]


class ShaderInvalidatingAttribute(views.Attribute):
    #TODO actually invalidate shaders
    pass


class AlphaTest(views.SubView):
    function0 = ShaderInvalidatingAttribute()
    reference0 = ShaderInvalidatingAttribute()
    function1 = ShaderInvalidatingAttribute()
    reference1 = ShaderInvalidatingAttribute()
    operator = ShaderInvalidatingAttribute()


class DepthMode(views.SubView):
    enable = views.Attribute()
    function = views.Attribute()
    update_enable = views.Attribute()


class BlendMode(views.SubView):
    function = views.Attribute()
    source_factor = views.Attribute()
    destination_factor = views.Attribute()
    logical_operation = views.Attribute()


class Material(gl.ResourceManagerMixin, views.View):

    def __init__(self, viewed_object):
        super().__init__(viewed_object)

        self.update_use_variables()

        fields = []

        def convert_color(c):
            return numpy.array([c.r,c.g,c.b,c.a],numpy.float32)/0xFF

        fields.append(('tev_color0',gl.vec4,convert_color(self.tev_colors[0])))
        fields.append(('tev_color1',gl.vec4,convert_color(self.tev_colors[1])))
        fields.append(('tev_color2',gl.vec4,convert_color(self.tev_colors[2])))
        fields.append(('tev_color_previous',gl.vec4,convert_color(self.tev_color_previous)))
        fields.append(('kcolor0',gl.vec4,convert_color(self.kcolors[0])))
        fields.append(('kcolor1',gl.vec4,convert_color(self.kcolors[1])))
        fields.append(('kcolor2',gl.vec4,convert_color(self.kcolors[2])))
        fields.append(('kcolor3',gl.vec4,convert_color(self.kcolors[3])))

        for i,channel in enumerate(self.enabled_channels):
            if self.use_material_color[i]:
                fields.append(('material_color{}'.format(i),gl.vec4,convert_color(channel.material_color)))
            if self.use_ambient_color[i]:
                fields.append(('ambient_color{}'.format(i),gl.vec4,convert_color(channel.ambient_color)))

        for i,matrix in enumerate(self.texture_matrices):
            if not self.use_texture_matrix[i]: continue
            if matrix.shape == gx.TG_MTX2x4:
                gl_type = gl.mat4x2
            elif matrix.shape == gx.TG_MTX3x4:
                gl_type = gl.mat4x3
            fields.append(('texture_matrix{}'.format(i),gl_type,matrix.create_matrix()))

        for i,matrix in enumerate(self.indirect_matrices):
            if not self.use_indirect_matrix[i]: continue
            gl_value = numpy.zeros((2,4),numpy.float32) #FIXME
            gl_value[:,0:3] = numpy.array(matrix.significand_matrix,numpy.float32)*2**matrix.scale_exponent
            fields.append(('indmatrix{}'.format(i),gl.mat3x2,gl_value))

        block_type = gl.uniform_block('MaterialBlock',((name,gl_type) for name,gl_type,_ in fields))
        block = self.gl_create_resource(block_type, GL_DYNAMIC_DRAW)

        for name,_,value in fields:
            block[name] = value

        self.gl_block = block

        self.gl_program_table = {}

    name = views.Attribute()
    unknown0 = views.Attribute()
    cull_mode = views.Attribute()

    channel_count = views.ReadOnlyAttribute()
    channels = views.ReadOnlyAttribute()

    texcoord_generator_count = views.ReadOnlyAttribute()
    texcoord_generators = views.ReadOnlyAttribute()
    texture_matrices = views.ReadOnlyAttribute()
    texture_indices = views.ReadOnlyAttribute()

    tev_stage_count = views.ReadOnlyAttribute()
    tev_stages = views.ReadOnlyAttribute()
    tev_colors = views.ReadOnlyAttribute()
    tev_color_previous = views.ReadOnlyAttribute()
    kcolors = views.ReadOnlyAttribute()
    swap_tables = views.ReadOnlyAttribute()

    indirect_stage_count = views.ReadOnlyAttribute()
    indirect_stages = views.ReadOnlyAttribute()
    indirect_matrices = views.ReadOnlyAttribute()

    alpha_test = views.SubViewAttribute(AlphaTest)
    fog = views.ReadOnlyAttribute()
    depth_test_early = ShaderInvalidatingAttribute()
    depth_mode = views.SubViewAttribute(DepthMode)
    blend_mode = views.SubViewAttribute(BlendMode)
    dither = views.Attribute()

    @property
    def enabled_channels(self):
        for i in range(min(self.channel_count, 2)):
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

    def update_use_variables(self):
        self.use_normal = False
        self.use_binormal = False
        self.use_tangent = False
        self.use_color = False
        self.use_texcoord = [False]*8
        self.use_material_color = [False]*2
        self.use_ambient_color = [False]*2
        self.use_texture_matrix = [False]*10
        self.use_texture = [False]*8
        self.use_indirect_matrix = [False]*3

        for i,channel in enumerate(self.enabled_channels):
            if channel.color_mode.material_source == gx.SRC_REG:
                self.use_material_color[i] = True
            elif channel.color_mode.material_source == gx.SRC_VTX:
                self.use_color = True
            else:
                raise ValueError('invalid material source')

            if channel.alpha_mode.material_source == gx.SRC_REG:
                self.use_material_color[i] = True
            elif channel.alpha_mode.material_source == gx.SRC_VTX:
                self.use_color = True
            else:
                raise ValueError('inavlid material source')

            if channel.color_mode.light_enable:
                if channel.color_mode.ambient_source == gx.SRC_REG:
                    self.use_ambient_color[i] = True
                elif channel.color_mode.ambient_source == gx.SRC_VTX:
                    self.use_color = True
                else:
                    raise ValueError('invalid ambient source')

            #if channel.alpha_mode.light_enable:
            #    if channel.alpha_mode.ambient_source == gx.SRC_REG:
            #        self.use_ambient_color[i] = True
            #    elif channel.alpha_mode.ambient_source == gx.SRC_VTX:
            #        self.use_color = True
            #    else:
            #        raise ValueError('invalid ambient source')

        for generator in self.enabled_texcoord_generators:
            if generator.function in {gx.TG_MTX2x4,gx.TG_MTX3x4}:
                if generator.source == gx.TG_NRM:
                    self.use_normal = True
                elif generator.source == gx.TG_BINRM:
                    self.use_binormal = True
                elif generator.source == gx.TG_TANGENT:
                    self.use_tangent = True
                elif generator.source in gx.TG_TEX:
                    self.use_texcoord[generator.source.index] = True

                if generator.matrix != gx.IDENTITY:
                    self.use_texture_matrix[generator.matrix.index] = True

        for stage in self.enabled_tev_stages:
            if stage.texture != gx.TEXMAP_NULL:
                self.use_texture[stage.texture.index] = True
            if stage.indirect_matrix in gx.ITM:
                self.use_indirect_matrix[stage.indirect_matrix.index] = True

        for stage in self.enabled_indirect_stages:
            self.use_texture[stage.texture.index] = True

    def gl_program(self, transformation_type):
        if transformation_type in self.gl_program_table:
            return self.gl_program_table[transformation_type]

        vertex_shader_string = views.vertex_shader.create_shader_string(self, transformation_type)
        fragment_shader_string = views.fragment_shader.create_shader_string(self)
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
        if self.blend_mode.source_factor == gx.BL_INVSDTALPHA:
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
        if self.blend_mode.destination_factor == gx.BL_INVSDTALPHA:
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

    def gl_bind(self, shape, textures):
        self.gl_block.bind(MATERIAL_BLOCK_BINDING_POINT)

        for i, texture_index in enumerate(self.texture_indices):
            if texture_index is None: continue
            textures[texture_index].gl_bind(TEXTURE_UNITS[i])

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

