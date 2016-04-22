from math import cos,sin,radians
import copy
import numpy
from OpenGL.GL import *
from btypes.big_endian import *
import gl
import gx
from j3d.opengl import *

import logging
logger = logging.getLogger(__name__)


class Vector(Struct):
    x = float32
    y = float32
    z = float32

    def __init__(self,x=0,y=0,z=0):
        self.x = x
        self.y = y
        self.z = z


class Color(Struct):
    r = uint8
    g = uint8
    b = uint8
    a = uint8

    def __init__(self,r=0x00,g=0x00,b=0x00,a=0xFF):
        self.r = r
        self.g = g
        self.b = b
        self.a = a

    @staticmethod
    def gl_type():
        return gl.vec4

    def gl_convert(self):
        return numpy.array([self.r,self.g,self.b,self.a],numpy.float32)/0xFF


class LightingMode(Struct):
    """Arguments to GXSetChanCtrl."""
    light_enable = bool8
    material_source = EnumConverter(uint8,gx.ChannelSource)
    light_mask = uint8
    diffuse_function = EnumConverter(uint8,gx.DiffuseFunction)
    attenuation_function = EnumConverter(uint8,gx.AttenuationFunction)
    ambient_source = EnumConverter(uint8,gx.ChannelSource)
    __padding__ = Padding(2)

    def __init__(self):
        self.light_enable = False
        self.material_source = gx.SRC_REG
        self.ambient_source = gx.SRC_REG
        self.light_mask = gx.LIGHT_NULL
        self.diffuse_function = gx.DF_NONE
        self.attenuation_function = gx.AF_NONE


class Channel:

    def __init__(self):
        self.color_mode = LightingMode()
        self.alpha_mode = LightingMode()
        self.material_color = Color(0xFF,0xFF,0xFF)
        self.ambient_color = Color(0xFF,0xFF,0xFF)


class Light(Struct):
    position = Vector
    direction = Vector
    color = Color
    a0 = float32
    a1 = float32
    a2 = float32
    k0 = float32
    k1 = float32
    k2 = float32

    def __init__(self):
        self.position = Vector(0,0,0)
        self.direction = Vector(0,0,0)
        self.color = (0xFF,0xFF,0xFF)
        self.a0 = 1
        self.a1 = 0
        self.a2 = 0
        self.k0 = 1
        self.k1 = 0
        self.k2 = 0


class TexCoordGenerator(Struct):
    """Arguments to GXSetTexCoordGen."""
    function = EnumConverter(uint8,gx.TexCoordFunction)
    source = EnumConverter(uint8,gx.TexCoordSource)
    matrix = EnumConverter(uint8,gx.TextureMatrix)
    __padding__ = Padding(1)

    def __init__(self):
        self.function = gx.TG_MTX2x4
        self.source = gx.TG_TEX0
        self.matrix = gx.IDENTITY


class TextureMatrix(Struct):
    shape = EnumConverter(uint8,gx.TexCoordFunction)
    matrix_type = uint8
    __padding__ = Padding(2)
    center_s = float32
    center_t = float32
    unknown0 = float32
    scale_s = float32
    scale_t = float32
    rotation = FixedPointConverter(sint16,180/32768)
    __padding__ = Padding(2)
    translation_s = float32
    translation_t = float32
    projection_matrix = Array(Array(float32,4),4)

    def __init__(self):
        self.matrix_type = 0
        self.shape = gx.TG_MTX2x4
        self.center_s = 0.5
        self.center_t = 0.5
        self.unknown0 = 0.5
        self.rotation = 0
        self.scale_s = 1
        self.scale_t = 1
        self.translation_s = 0
        self.translation_t = 0
        self.projection_matrix = [[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]]

    def create_matrix(self):
        c = cos(radians(self.rotation))
        s = sin(radians(self.rotation))
        R = numpy.matrix([[c,-s,0],[s,c,0],[0,0,1]])
        S = numpy.matrix([[self.scale_s,0,0],[0,self.scale_t,0],[0,0,1]])
        C = numpy.matrix([[1,0,self.center_s],[0,1,self.center_t],[0,0,1]])
        T = numpy.matrix([[1,0,self.translation_s],[0,1,self.translation_t],[0,0,1]])

        # Only types 0x00, 0x06, 0x07, 0x08 and 0x09 have been tested
        if self.matrix_type in {0x00,0x02,0x0A,0x0B,0x80}:
            P = numpy.matrix([[1,0,0,0],[0,1,0,0],[0,0,0,1]])
        elif self.matrix_type == 0x06:
            P = numpy.matrix([[0.5,0,0,0.5],[0,-0.5,0,0.5],[0,0,0,1]])
        elif self.matrix_type == 0x07:
            P = numpy.matrix([[0.5,0,0.5,0],[0,-0.5,0.5,0],[0,0,1,0]])
        elif self.matrix_type in {0x08,0x09}:
            P = numpy.matrix([[0.5,0,0.5,0],[0,-0.5,0.5,0],[0,0,1,0]])*numpy.matrix(self.projection_matrix)
        else:
            raise ValueError('invalid texture matrix type')

        M = T*C*S*R*C.I*P

        if self.shape == gx.TG_MTX2x4:
            return M[:2,:]
        elif self.shape == gx.TG_MTX3x4:
            return M
        else:
            raise ValueError('invalid texture matrix shape')

    def gl_type(self):
        if self.shape == gx.TG_MTX2x4:
            return gl.mat4x2
        if self.shape == gx.TG_MTX3x4:
            return gl.mat4x3

        raise ValueError('invalid texture matrix shape')

    def gl_convert(self):
        return self.create_matrix()


class TevColorMode(Struct):
    """Arguments to GXSetTevColorIn and GXSetTevColorOp."""
    a = EnumConverter(uint8,gx.ColorInput)
    b = EnumConverter(uint8,gx.ColorInput)
    c = EnumConverter(uint8,gx.ColorInput)
    d = EnumConverter(uint8,gx.ColorInput)
    function = EnumConverter(uint8,gx.TevFunction)
    bias = EnumConverter(uint8,gx.TevBias)
    scale = EnumConverter(uint8,gx.TevScale)
    clamp = bool8
    output = EnumConverter(uint8,gx.TevColor)

    def __init__(self):
        self.a = gx.CC_ZERO
        self.b = gx.CC_ZERO
        self.c = gx.CC_ZERO
        self.d = gx.CC_TEXC
        self.function = gx.TEV_ADD
        self.bias = gx.TB_ZERO
        self.scale = gx.CS_SCALE_1
        self.clamp = True
        self.output = gx.TEVPREV


class TevAlphaMode(Struct):
    """Arguments to GXSetTevAlphaIn and GXSetTevAlphaOp."""
    a = EnumConverter(uint8,gx.AlphaInput)
    b = EnumConverter(uint8,gx.AlphaInput)
    c = EnumConverter(uint8,gx.AlphaInput)
    d = EnumConverter(uint8,gx.AlphaInput)
    function = EnumConverter(uint8,gx.TevFunction)
    bias = EnumConverter(uint8,gx.TevBias)
    scale = EnumConverter(uint8,gx.TevScale)
    clamp = bool8
    output = EnumConverter(uint8,gx.TevColor)

    def __init__(self):
        self.a = gx.CA_ZERO
        self.b = gx.CA_ZERO
        self.c = gx.CA_ZERO
        self.d = gx.CA_TEXA
        self.function = gx.TEV_ADD
        self.bias = gx.TB_ZERO
        self.scale = gx.CS_SCALE_1
        self.clamp = True
        self.output = gx.TEVPREV


class TevStage:

    def __init__(self):
        self.unknown0 = 0xFF
        self.unknown1 = 0xFF

        self.texcoord = gx.TEXCOORD_NULL
        self.texture = gx.TEXMAP_NULL
        self.color = gx.COLOR_NULL

        self.color_mode = TevColorMode()
        self.alpha_mode = TevAlphaMode()

        self.constant_color = gx.TEV_KCSEL_1
        self.constant_alpha = gx.TEV_KASEL_1

        self.color_swap_table = gx.TEV_SWAP0
        self.texture_swap_table = gx.TEV_SWAP0

        self.indirect_stage = gx.INDTEXSTAGE0
        self.indirect_format = gx.ITF_8
        self.indirect_bias_components = gx.ITB_NONE
        self.indirect_matrix = gx.ITM_OFF
        self.wrap_s = gx.ITW_OFF
        self.wrap_t = gx.ITW_OFF
        self.add_previous_texcoord = False
        self.use_original_lod = False
        self.bump_alpha = gx.ITBA_OFF


class SwapTable(Struct):
    """Arguments to GXSetTevSwapModeTable."""
    r = EnumConverter(uint8,gx.ColorComponent)
    g = EnumConverter(uint8,gx.ColorComponent)
    b = EnumConverter(uint8,gx.ColorComponent)
    a = EnumConverter(uint8,gx.ColorComponent)

    def __init__(self):
        self.r = gx.CH_RED
        self.g = gx.CH_GREEN
        self.b = gx.CH_BLUE
        self.a = gx.CH_ALPHA


class IndirectStage:

    def __init__(self):
        self.texcoord = gx.TEXCOORD_NULL
        self.texture = gx.TEXMAP_NULL
        self.scale_s = gx.ITS_1
        self.scale_t = gx.ITS_1


class IndirectMatrix(Struct):
    """Arguments to GXSetIndTexMatrix."""
    significand_matrix = Array(Array(float32,3),2)
    scale_exponent = sint8
    __padding__ = Padding(3)

    def __init__(self):
        self.significand_matrix = [[0.5,0,0],[0,0.5,0]]
        self.scale_exponent = 1

    @staticmethod
    def gl_type():
        return gl.mat3x2

    def gl_convert(self):
        matrix = numpy.zeros((2,4),numpy.float32) #FIXME
        matrix[:,0:3] = numpy.array(self.significand_matrix,numpy.float32)*2**self.scale_exponent
        return matrix


class AlphaTest(Struct):
    """Arguments to GXSetAlphaCompare."""
    function0 = EnumConverter(uint8,gx.CompareFunction)
    reference0 = uint8
    operation = EnumConverter(uint8,gx.AlphaOperator)
    function1 = EnumConverter(uint8,gx.CompareFunction)
    reference1 = uint8
    __padding__ = Padding(3)

    def __init__(self):
        self.function0 = gx.ALWAYS
        self.reference0 = 0
        self.function1 = gx.ALWAYS
        self.reference1 = 0
        self.operation = gx.AOP_AND


class Fog(Struct):
    """Arguments to GXSetFog and GXSetFogRangeAdj."""
    function = EnumConverter(uint8,gx.FogFunction)
    range_adjustment_enable = bool8
    range_adjustment_center = uint16
    z_start = float32
    z_end = float32
    z_near = float32
    z_far = float32
    color = Color
    range_adjustment_table = Array(uint16,10)

    def __init__(self):
        self.function = gx.FOG_NONE
        self.z_start = 0
        self.z_end = 0
        self.z_near = 0
        self.z_far = 0
        self.color = Color(0xFF,0xFF,0xFF)

        self.range_adjustment_enable = False
        self.range_adjustment_center = 0
        self.range_adjustment_table = [0]*10


class DepthMode(Struct):
    """Arguments to GXSetZMode."""
    enable = bool8
    function = EnumConverter(uint8,gx.CompareFunction)
    update_enable = bool8
    __padding__ = Padding(1)

    def __init__(self):
        self.enable = True
        self.function = gx.LEQUAL
        self.update_enable = True


class BlendMode(Struct):
    """Arguments to GXSetBlendMode."""
    function = EnumConverter(uint8,gx.BlendFunction)
    source_factor = EnumConverter(uint8,gx.BlendSourceFactor)
    destination_factor = EnumConverter(uint8,gx.BlendDestinationFactor)
    logical_operation = EnumConverter(uint8,gx.LogicalOperation)

    def __init__(self):
        self.function = gx.BM_NONE
        self.source_factor = gx.BL_SRCALPHA
        self.destination_factor = gx.BL_INVSRCALPHA
        self.logical_operation = gx.LO_CLEAR


class UnknownStruct5(Struct):
    unknown0 = uint8
    __padding__ = Padding(3)
    unknown1 = float32
    unknown2 = float32
    unknown3 = float32

    def __init__(self):
        self.unknown0 = 0
        self.unknown1 = 1
        self.unknown2 = 1
        self.unknown3 = 1
        
    @classmethod
    def unpack(cls,stream):
        unknown5 = super().unpack(stream)
        if unknown5 != UnknownStruct5():
            logger.warning('unknown5 different from default')
        return unknown5


class Material:

    def __init__(self):
        self.name = None
        self.unknown0 = 1 # related to transparency sorting
        self.cull_mode = gx.CULL_BACK

        self.channel_count = 0
        self.channels = [Channel() for _ in range(2)]
        self.lights = [None]*8

        self.texcoord_generator_count = 0
        self.texcoord_generators = [TexCoordGenerator() for _ in range(8)]
        self.texture_matrices = [None]*10
        self.texture_indices = [None]*8

        self.tev_stage_count = 0
        self.tev_stages = [TevStage() for _ in range(16)]
        self.tev_colors = [Color(0xFF,0xFF,0xFF) for _ in range(3)]
        self.tev_color_previous = Color(0xFF,0xFF,0xFF)
        self.kcolors = [Color(0xFF,0xFF,0xFF) for _ in range(4)]
        self.swap_tables = [SwapTable() for _ in range(4)]

        self.indirect_stage_count = 0
        self.indirect_stages = [IndirectStage() for _ in range(4)]
        self.indirect_matrices = [IndirectMatrix() for _ in range(3)]

        self.alpha_test = AlphaTest()
        self.fog = Fog()
        self.depth_test_early = True
        self.depth_mode = DepthMode()
        self.blend_mode = BlendMode()
        self.dither = True
        self.unknown5 = UnknownStruct5()

        self.unknown2 = [0xFFFF]*8
        self.unknown3 = [0xFFFF]*20
        self.unknown4 = [0xFFFF]*12

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

    def gl_init(self):
        self.update_use_variables()

        fields = []

        fields.append(('tev_color0',self.tev_colors[0]))
        fields.append(('tev_color1',self.tev_colors[1]))
        fields.append(('tev_color2',self.tev_colors[2]))
        fields.append(('tev_color_previous',self.tev_color_previous))
        fields.append(('kcolor0',self.kcolors[0]))
        fields.append(('kcolor1',self.kcolors[1]))
        fields.append(('kcolor2',self.kcolors[2]))
        fields.append(('kcolor3',self.kcolors[3]))

        for i,channel in enumerate(self.enabled_channels):
            if self.use_material_color[i]:
                fields.append(('material_color{}'.format(i),channel.material_color))
            if self.use_ambient_color[i]:
                fields.append(('ambient_color{}'.format(i),channel.ambient_color))

        for i,matrix in enumerate(self.texture_matrices):
            if not self.use_texture_matrix[i]: continue
            fields.append(('texture_matrix{}'.format(i),matrix))

        for i,matrix in enumerate(self.indirect_matrices):
            if not self.use_indirect_matrix[i]: continue
            fields.append(('indmatrix{}'.format(i),matrix))

        block_type = gl.uniform_block('MaterialBlock',((name,value.gl_type()) for name,value in fields))
        self.gl_block = block_type(GL_DYNAMIC_DRAW)

        for name,value in fields:
            self.gl_block[name] = value.gl_convert()

        self.gl_texture_indices = copy.copy(self.texture_indices)

    def gl_bind(self,textures):
        self.gl_block.bind(MATERIAL_BLOCK_BINDING_POINT)

        for i,texture_index in enumerate(self.gl_texture_indices):
            if texture_index is None: continue
            textures[texture_index].gl_bind(TEXTURE_UNITS[i])

        if self.cull_mode != gx.CULL_NONE:
            glEnable(GL_CULL_FACE)
            glCullFace(self.cull_mode.gl_value)
        else:
            glDisable(GL_CULL_FACE)

        if self.depth_mode.enable:
            glEnable(GL_DEPTH_TEST)
            glDepthFunc(self.depth_mode.function.gl_value)
            glDepthMask(self.depth_mode.update_enable)
        else:
            glDisable(GL_DEPTH_TEST)

        if self.blend_mode.function == gx.BM_BLEND:
            glEnable(GL_BLEND)
            glBlendEquation(GL_FUNC_ADD)
            glBlendFunc(self.blend_mode.source_factor.gl_value,self.blend_mode.destination_factor.gl_value)
        elif self.blend_mode.function == gx.BM_SUBTRACT:
            glEnable(GL_BLEND)
            glBlendEquation(GL_FUNC_REVERSE_SUBTRACT)
            glBlendFunc(GL_ONE,GL_ONE)
        else:
            glDisable(GL_BLEND)

        if self.blend_mode.function == gx.BM_LOGIC:
            glEnable(GL_COLOR_LOGIC_OP)
            glLogicOp(self.blend_mode.logical_operation.gl_value)
        else:
            glDisable(GL_COLOR_LOGIC_OP)

        if self.dither:
            glEnable(GL_DITHER)
        else:
            glDisable(GL_DITHER)

