from math import cos,sin,radians
import functools
from collections import namedtuple
import numpy
from btypes.big_endian import *
import gx
import j3d.string_table

import logging
logger = logging.getLogger(__name__)

offset32 = NoneableConverter(uint32, 0)

index8 = NoneableConverter(uint8, 0xFF)
index16 = NoneableConverter(uint16, 0xFFFF)


class Header(Struct):
    magic = ByteString(4)
    section_size = uint32
    material_count = uint16
    __padding__ = Padding(2)
    entry_offset = offset32
    entry_index_offset = offset32
    name_offset = offset32
    indirect_entry_offset = offset32
    cull_mode_offset = offset32
    material_color_offset = offset32
    channel_count_offset = offset32
    lighting_mode_offset = offset32
    ambient_color_offset = offset32
    light_offset = offset32
    texcoord_generator_count_offset = offset32
    texcoord_generator_offset = offset32
    unknown2_offset = offset32 # noclip.website: post tex gen table
    texture_matrix_offset = offset32
    unknown3_offset = offset32 # noclip.website: post tex mtx table
    texture_index_offset = offset32
    tev_order_offset = offset32
    tev_color_offset = offset32
    kcolor_offset = offset32
    tev_stage_count_offset = offset32
    tev_combiner_offset = offset32
    swap_mode_offset = offset32
    swap_table_offset = offset32
    fog_offset = offset32
    alpha_test_offset = offset32
    blend_mode_offset = offset32
    depth_mode_offset = offset32
    depth_test_early_offset = offset32
    dither_offset = offset32
    unknown5_offset = offset32

    def __init__(self):
        self.magic = b'MAT3'
        self.unknown3_offset = None

    @classmethod
    def unpack(cls, stream):
        header = super().unpack(stream)
        if header.magic != b'MAT3':
            raise FormatError('invalid magic')
        if header.unknown3_offset is not None:
            logger.warning('unknown3_offset different from default')
        return header


class Vector(Struct):
    x = float32
    y = float32
    z = float32

    def __init__(self, x=0, y=0, z=0):
        self.x = x
        self.y = y
        self.z = z


class Color(Struct):
    r = uint8
    g = uint8
    b = uint8
    a = uint8

    def __init__(self, r=0x00, g=0x00, b=0x00, a=0xFF):
        self.r = r
        self.g = g
        self.b = b
        self.a = a


class ColorS16(Struct):
    r = sint16
    g = sint16
    b = sint16
    a = sint16

    def __init__(self, r=0x00, g=0x00, b=0x00, a=0xFF):
        self.r = r
        self.g = g
        self.b = b
        self.a = a


class LightingMode(Struct):
    """Arguments to GXSetChanCtrl."""
    light_enable = bool8
    material_source = EnumConverter(uint8, gx.ChannelSource)
    light_mask = uint8
    diffuse_function = EnumConverter(uint8, gx.DiffuseFunction)
    attenuation_function = EnumConverter(uint8, gx.AttenuationFunction)
    ambient_source = EnumConverter(uint8, gx.ChannelSource)
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
        self.material_color = Color(0xFF, 0xFF, 0xFF)
        self.ambient_color = Color(0xFF, 0xFF, 0xFF)


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
        self.position = Vector(0, 0, 0)
        self.direction = Vector(0, 0, 0)
        self.color = (0xFF, 0xFF, 0xFF)
        self.a0 = 1
        self.a1 = 0
        self.a2 = 0
        self.k0 = 1
        self.k1 = 0
        self.k2 = 0


class TexCoordGenerator(Struct):
    """Arguments to GXSetTexCoordGen."""
    function = EnumConverter(uint8, gx.TexCoordFunction)
    source = EnumConverter(uint8, gx.TexCoordSource)
    matrix = EnumConverter(uint8, gx.TextureMatrix)
    __padding__ = Padding(1)

    def __init__(self):
        self.function = gx.TG_MTX2x4
        self.source = gx.TG_TEX0
        self.matrix = gx.IDENTITY


class TextureMatrix(Struct):
    shape = EnumConverter(uint8, gx.TexCoordFunction)
    matrix_type = uint8
    __padding__ = Padding(2)
    center_s = float32
    center_t = float32
    unknown0 = float32 # noclip.website: center q
    scale_s = float32
    scale_t = float32
    rotation = FixedPointConverter(sint16, 180/32768)
    __padding__ = Padding(2)
    translation_s = float32
    translation_t = float32
    projection_matrix = Array(Array(float32, 4), 4) # noclip.website: effect matrix

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
        self.projection_matrix = [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]

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


class TevOrder(Struct):
    """Arguments to GXSetTevOrder."""
    texcoord = EnumConverter(uint8, gx.TexCoord)
    texture = EnumConverter(uint8, gx.Texture)
    color = EnumConverter(uint8, gx.Channel)
    __padding__ = Padding(1)


class TevColorMode(Struct):
    """Arguments to GXSetTevColorIn and GXSetTevColorOp."""
    a = EnumConverter(uint8, gx.ColorInput)
    b = EnumConverter(uint8, gx.ColorInput)
    c = EnumConverter(uint8, gx.ColorInput)
    d = EnumConverter(uint8, gx.ColorInput)
    function = EnumConverter(uint8, gx.TevFunction)
    bias = EnumConverter(uint8, gx.TevBias)
    scale = EnumConverter(uint8, gx.TevScale)
    clamp = bool8
    output = EnumConverter(uint8, gx.TevColor)

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
    a = EnumConverter(uint8, gx.AlphaInput)
    b = EnumConverter(uint8, gx.AlphaInput)
    c = EnumConverter(uint8, gx.AlphaInput)
    d = EnumConverter(uint8, gx.AlphaInput)
    function = EnumConverter(uint8, gx.TevFunction)
    bias = EnumConverter(uint8, gx.TevBias)
    scale = EnumConverter(uint8, gx.TevScale)
    clamp = bool8
    output = EnumConverter(uint8, gx.TevColor)

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


class TevCombiner(Struct):
    unknown0 = uint8
    color_mode = TevColorMode
    alpha_mode = TevAlphaMode
    unknown1 = uint8
    
    @classmethod
    def unpack(cls, stream):
        tev_combiner = super().unpack(stream)
        if tev_combiner.unknown0 != 0xFF:
            logger.warning('tev combiner unknown0 different from default')
        if tev_combiner.unknown1 != 0xFF:
            logger.warning('tev combiner unknown1 different from default')
        return tev_combiner


class SwapMode(Struct):
    """Arguments to GXSetTevSwapMode."""
    color_swap_table = EnumConverter(uint8, gx.SwapTable)
    texture_swap_table = EnumConverter(uint8, gx.SwapTable)
    __padding__ = Padding(2)


class TevIndirect(Struct):
    """Arguments to GXSetTevIndirect."""
    indirect_stage = EnumConverter(uint8, gx.IndirectStage)
    indirect_format = EnumConverter(uint8, gx.IndirectFormat)
    indirect_bias_components = EnumConverter(uint8, gx.IndirectBiasComponents)
    indirect_matrix = EnumConverter(uint8, gx.IndirectMatrix)
    wrap_s = EnumConverter(uint8, gx.IndirectWrap)
    wrap_t = EnumConverter(uint8, gx.IndirectWrap)
    add_previous_texcoord = bool8
    use_original_lod = bool8
    bump_alpha = EnumConverter(uint8, gx.IndirectBumpAlpha)
    __padding__ = Padding(3)


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
    r = EnumConverter(uint8, gx.ColorComponent)
    g = EnumConverter(uint8, gx.ColorComponent)
    b = EnumConverter(uint8, gx.ColorComponent)
    a = EnumConverter(uint8, gx.ColorComponent)

    def __init__(self):
        self.r = gx.CH_RED
        self.g = gx.CH_GREEN
        self.b = gx.CH_BLUE
        self.a = gx.CH_ALPHA


class IndirectOrder(Struct):
    """Arguments to GXSetIndTexOrder."""
    texcoord = EnumConverter(uint8, gx.TexCoord)
    texture = EnumConverter(uint8, gx.Texture)
    __padding__ = Padding(2)


class IndirectTexCoordScale(Struct):
    """Arguments to GXSetIndTexCoordScale."""
    scale_s = EnumConverter(uint8, gx.IndirectScale)
    scale_t = EnumConverter(uint8, gx.IndirectScale)
    __padding__ = Padding(2)


class IndirectStage:

    def __init__(self):
        self.texcoord = gx.TEXCOORD_NULL
        self.texture = gx.TEXMAP_NULL
        self.scale_s = gx.ITS_1
        self.scale_t = gx.ITS_1


class IndirectMatrix(Struct):
    """Arguments to GXSetIndTexMatrix."""
    significand_matrix = Array(Array(float32, 3), 2)
    scale_exponent = sint8
    __padding__ = Padding(3)

    def __init__(self):
        self.significand_matrix = [[0.5, 0, 0], [0, 0.5, 0]]
        self.scale_exponent = 1


class AlphaTest(Struct):
    """Arguments to GXSetAlphaCompare."""
    function0 = EnumConverter(uint8, gx.CompareFunction)
    reference0 = uint8
    operator = EnumConverter(uint8, gx.AlphaOperator)
    function1 = EnumConverter(uint8, gx.CompareFunction)
    reference1 = uint8
    __padding__ = Padding(3)

    def __init__(self):
        self.function0 = gx.ALWAYS
        self.reference0 = 0
        self.function1 = gx.ALWAYS
        self.reference1 = 0
        self.operator = gx.AOP_AND


class Fog(Struct):
    """Arguments to GXSetFog and GXSetFogRangeAdj."""
    function = EnumConverter(uint8, gx.FogFunction)
    range_adjustment_enable = bool8
    range_adjustment_center = uint16
    z_start = float32
    z_end = float32
    z_near = float32
    z_far = float32
    color = Color
    range_adjustment_table = Array(uint16, 10)

    def __init__(self):
        self.function = gx.FOG_NONE
        self.z_start = 0
        self.z_end = 0
        self.z_near = 0
        self.z_far = 0
        self.color = Color(0xFF, 0xFF, 0xFF)

        self.range_adjustment_enable = False
        self.range_adjustment_center = 0
        self.range_adjustment_table = [0]*10


class DepthMode(Struct):
    """Arguments to GXSetZMode."""
    enable = bool8
    function = EnumConverter(uint8, gx.CompareFunction)
    update_enable = bool8
    __padding__ = Padding(1)

    def __init__(self):
        self.enable = True
        self.function = gx.LEQUAL
        self.update_enable = True


class BlendMode(Struct):
    """Arguments to GXSetBlendMode."""
    function = EnumConverter(uint8, gx.BlendFunction)
    source_factor = EnumConverter(uint8, gx.BlendSourceFactor)
    destination_factor = EnumConverter(uint8, gx.BlendDestinationFactor)
    logical_operation = EnumConverter(uint8, gx.LogicalOperation)

    def __init__(self):
        self.function = gx.BM_NONE
        self.source_factor = gx.BL_SRCALPHA
        self.destination_factor = gx.BL_INVSRCALPHA
        self.logical_operation = gx.LO_CLEAR


class UnknownStruct2(Struct):
    unknown0 = uint8
    unknown1 = uint8
    unknown2 = uint8
    unknown3 = uint8
    unknown4 = uint32

    def __init__(self):
        self.unknown0 = 1
        self.unknown1 = 4
        self.unknown2 = 0x3C
        self.unknown3 = 0xFF
        self.unknown4 = 0xFFFFFFFF
        
    @classmethod
    def unpack(cls, stream):
        unknown2 = super().unpack(stream)
        if unknown2 != UnknownStruct2():
            logger.warning('unknown2 different from default')
        return unknown2


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
    def unpack(cls, stream):
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
        self.tev_colors = [Color(0xFF, 0xFF, 0xFF) for _ in range(3)]
        self.tev_color_previous = Color(0xFF, 0xFF, 0xFF)
        self.kcolors = [Color(0xFF, 0xFF, 0xFF) for _ in range(4)]
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

        self.unknown2 = [None]*8
        self.unknown3 = [0xFFFF]*20
        self.unknown4 = [0xFFFF]*12
        self.unknown5 = UnknownStruct5()

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


class ChannelEntry(Struct):
    color_mode_index = index16
    alpha_mode_index = index16

    def __init__(self):
        self.color_mode_index = None
        self.alpha_mode_index = None


class Entry(Struct):
    unknown0 = uint8 # noclip.website: material mode
    cull_mode_index = index8
    channel_count_index = index8
    texcoord_generator_count_index = index8
    tev_stage_count_index = index8
    depth_test_early_index = index8
    depth_mode_index = index8
    dither_index = index8
    material_color_indices = Array(index16, 2)
    channels = Array(ChannelEntry, 2)
    ambient_color_indices = Array(index16, 2)
    light_indices = Array(index16, 8)
    texcoord_generator_indices = Array(index16, 8)
    unknown2_indices = Array(index16, 8)
    texture_matrix_indices = Array(index16, 10)
    unknown3 = Array(uint16, 20)
    texture_index_indices = Array(index16, 8)
    kcolor_indices = Array(index16, 4)
    constant_colors = Array(EnumConverter(uint8, gx.ConstantColor), 16)
    constant_alphas = Array(EnumConverter(uint8, gx.ConstantAlpha), 16)
    tev_order_indices = Array(index16, 16)
    tev_color_indices = Array(index16, 3)
    tev_color_previous_index = index16
    tev_combiner_indices = Array(index16, 16)
    swap_mode_indices = Array(index16, 16)
    swap_table_indices = Array(index16, 4)
    unknown4 = Array(uint16, 12)
    fog_index = index16
    alpha_test_index = index16
    blend_mode_index = index16
    unknown5_index = index16

    def __init__(self):
        self.unknown0 = 1
        self.cull_mode_index = None
        self.channel_count_index = None
        self.texcoord_generator_count_index = None
        self.tev_stage_count_index = None
        self.depth_test_early_index = None
        self.depth_mode_index = None
        self.dither_index = None
        self.material_color_indices = [None]*2
        self.channels = [ChannelEntry() for _ in range(2)]
        self.ambient_color_indices = [None]*2
        self.light_indices = [None]*8
        self.texcoord_generator_indices = [None]*8
        self.unknown2_indices = [None]*8
        self.texture_matrix_indices = [None]*10
        self.unknown3 = [0xFFFF]*20
        self.texture_index_indices = [None]*8
        self.kcolor_indices = [None]*4
        self.constant_colors = [gx.TEV_KCSEL_1]*16
        self.constant_alphas = [gx.TEV_KASEL_1]*16
        self.tev_order_indices = [None]*16
        self.tev_color_indices = [None]*3
        self.tev_color_previous_index = None
        self.tev_combiner_indices = [None]*16
        self.swap_mode_indices = [None]*16
        self.swap_table_indices = [None]*4
        self.unknown4 = [0xFFFF]*12
        self.fog_index = None
        self.alpha_test_index = None
        self.blend_mode_index = None
        self.unknown5_index = None


class IndirectEntry(Struct):
    unknown0 = uint8 # enable or indirect stage count? noclip.website: enable
    unknown1 = uint8 # enable or indirect stage count? noclip.website: indirect stage count
    __padding__ = Padding(2)
    indirect_orders = Array(IndirectOrder, 4)
    indirect_matrices = Array(IndirectMatrix, 3)
    indirect_texcoord_scales = Array(IndirectTexCoordScale, 4)
    tev_indirects = Array(TevIndirect, 16)

    def __init__(self):
        self.tev_indirects = [TevIndirect() for _ in range(16)]
        self.indirect_orders = [IndirectOrder() for _ in range(4)]
        self.indirect_texcoord_scales = [IndirectTexCoordScale() for _ in range(4)]
        self.indirect_matrices = [IndirectMatrix() for _ in range(3)]

    @classmethod
    def unpack(cls, stream):
        indirect_entry = super().unpack(stream)
        if indirect_entry.unknown0 != indirect_entry.unknown1 or indirect_entry.unknown0 not in {0, 1}:
            raise FormatError('unsuported indirect texture entry unknown0 and unknown1')
        return indirect_entry


class Pool: #<-?

    def __init__(self, values=tuple(), equal_predicate=None):
        self.values = list(values)
        if equal_predicate is not None:
            self.equal = equal_predicate

    def __getitem__(self, value):
        for i in range(len(self.values)):
            if self.equal(value, self.values[i]):
                return i

        self.values.append(value)
        return len(self.values) - 1

    def __iter__(self):
        yield from self.values

    @staticmethod
    def equal(a, b):
        return a == b


class TypedSequence: #<-?

    def __init__(self, element_type, sequence):
        self.element_type = element_type
        self.sequence = sequence

    @staticmethod
    def pack(stream, sequence):
        for element in sequence.sequence:
            sequence.element_type.pack(stream, element)


class ArrayUnpacker: #<-?

    def __init__(self, stream, offset, element_type):
        self.stream = stream
        self.offset = offset
        self.element_type = element_type

    def __getitem__(self, index):
        self.stream.seek(self.offset + index*self.element_type.sizeof())
        return self.element_type.unpack(self.stream)


def decorator_factory(function):
    def wrapper(*args, **kwargs):
        return functools.partial(function, *args, **kwargs)
    return wrapper


@decorator_factory
def pool_load_method(element_type, load_function, **kwargs):
    def wrapper(materials, entries):
        pool = Pool(**kwargs)
        for material, entry in zip(materials, entries):
            load_function(pool, material, entry)
        return TypedSequence(element_type, pool)
    return staticmethod(wrapper)


@decorator_factory
def pool_unload_method(element_type, unload_function):
    def wrapper(stream, offset, materials, entries):
        array = ArrayUnpacker(stream, offset, element_type) if offset is not None else None
        for material, entry in zip(materials, entries):
            unload_function(array, material, entry)
    return staticmethod(wrapper)


def equal_tev_combiner_and_swap_mode(a, b):
    return TevCombiner.__eq__(a, b) and SwapMode.__eq__(a, b)


class SectionPacker:

    entry_type = Entry

    def pack(self, stream, materials):
        entries = [self.entry_type() for _ in range(len(materials))]

        for material, entry in zip(materials, entries):
            entry.unknown0 = material.unknown0
            entry.unknown3 = material.unknown3
            entry.unknown4 = material.unknown4
            self.load_constant_colors(material, entry)
            self.load_constant_alphas(material, entry)

        indirect_entries = self.create_indirect_entries(materials)

        def pool(pool_function): #<-?
            return pool_function(materials, entries)

        cull_mode_pool = pool(self.pool_cull_mode)
        channel_count_pool = pool(self.pool_channel_count)
        material_color_pool = pool(self.pool_material_color)
        ambient_color_pool = pool(self.pool_ambient_color)
        lighting_mode_pool = pool(self.pool_lighting_mode)
        light_pool = pool(self.pool_light)
        texcoord_generator_count_pool = pool(self.pool_texcoord_generator_count)
        texcoord_generator_pool = pool(self.pool_texcoord_generator)
        unknown2_pool = pool(self.pool_unknown2)
        texture_matrix_pool = pool(self.pool_texture_matrix)
        texture_index_pool = pool(self.pool_texture_index)
        tev_stage_count_pool = pool(self.pool_tev_stage_count)
        tev_order_pool = pool(self.pool_tev_order)
        tev_combiner_pool = pool(self.pool_tev_combiner)
        swap_mode_pool = pool(self.pool_swap_mode)
        tev_color_pool = pool(self.pool_tev_color)
        kcolor_pool = pool(self.pool_kcolor)
        swap_table_pool = pool(self.pool_swap_table)
        fog_pool = pool(self.pool_fog)
        alpha_test_pool = pool(self.pool_alpha_test)
        blend_mode_pool = pool(self.pool_blend_mode)
        depth_mode_pool = pool(self.pool_depth_mode)
        depth_test_early_pool = pool(self.pool_depth_test_early)
        dither_pool = pool(self.pool_dither)
        unknown5_pool = pool(self.pool_unknown5)

        entry_pool = Pool()
        entry_indices = [entry_pool[entry] for entry in entries]

        base = stream.tell()
        header = Header()
        header.material_count = len(materials)
        stream.write(b'\x00'*Header.sizeof())

        header.entry_offset = stream.tell() - base
        for entry in entry_pool:
            self.entry_type.pack(stream, entry)

        header.entry_index_offset = stream.tell() - base
        for index in entry_indices:
            uint16.pack(stream, index)

        align(stream, 4)
        header.name_offset = stream.tell() - base
        j3d.string_table.pack(stream, (material.name for material in materials))

        def pack_pool(pool): #<-?
            if pool is None: return None
            offset = stream.tell() - base
            TypedSequence.pack(stream, pool)
            return offset

        align(stream, 4)
        header.indirect_entry_offset = pack_pool(indirect_entries)

        align(stream, 4)
        header.cull_mode_offset = pack_pool(cull_mode_pool)
        header.material_color_offset = pack_pool(material_color_pool)
        header.channel_count_offset = pack_pool(channel_count_pool)
        align(stream, 4)
        header.lighting_mode_offset = pack_pool(lighting_mode_pool)
        header.ambient_color_offset = pack_pool(ambient_color_pool)
        header.light_offset = pack_pool(light_pool)
        header.texcoord_generator_count_offset = pack_pool(texcoord_generator_count_pool)
        align(stream, 4)
        header.texcoord_generator_offset = pack_pool(texcoord_generator_pool)
        header.unknown2_offset = pack_pool(unknown2_pool)
        header.texture_matrix_offset = pack_pool(texture_matrix_pool)
        header.texture_index_offset = pack_pool(texture_index_pool)
        align(stream, 4)
        header.tev_order_offset = pack_pool(tev_order_pool)
        header.tev_color_offset = pack_pool(tev_color_pool)
        header.kcolor_offset = pack_pool(kcolor_pool)
        header.tev_stage_count_offset = pack_pool(tev_stage_count_pool)
        align(stream, 4)
        header.tev_combiner_offset = pack_pool(tev_combiner_pool)
        header.swap_mode_offset = pack_pool(swap_mode_pool)
        header.swap_table_offset = pack_pool(swap_table_pool)
        header.fog_offset = pack_pool(fog_pool)
        header.alpha_test_offset = pack_pool(alpha_test_pool)
        header.blend_mode_offset = pack_pool(blend_mode_pool)
        header.depth_mode_offset = pack_pool(depth_mode_pool)
        header.depth_test_early_offset = pack_pool(depth_test_early_pool)
        align(stream, 4)
        header.dither_offset = pack_pool(dither_pool)
        align(stream, 4)
        header.unknown5_offset = pack_pool(unknown5_pool)

        align(stream, 0x20)
        header.section_size = stream.tell() - base
        stream.seek(base)
        Header.pack(stream, header)
        stream.seek(base + header.section_size)

    def load_constant_colors(self, material, entry):
        for i, stage in enumerate(material.tev_stages):
            entry.constant_colors[i] = stage.constant_color

    def load_constant_alphas(self, material, entry):
        for i, stage in enumerate(material.tev_stages):
            entry.constant_alphas[i] = stage.constant_alpha

    def create_indirect_entries(self, materials):
        return TypedSequence(IndirectEntry, [self.create_indirect_entry(material) for material in materials])

    def create_indirect_entry(self, material):
        entry = IndirectEntry()

        entry.unknown0 = material.indirect_stage_count
        entry.unknown1 = material.indirect_stage_count

        for stage, tev_indirect in zip(material.tev_stages, entry.tev_indirects):
            tev_indirect.indirect_stage = stage.indirect_stage
            tev_indirect.indirect_format = stage.indirect_format
            tev_indirect.indirect_bias_components = stage.indirect_bias_components
            tev_indirect.indirect_matrix = stage.indirect_matrix
            tev_indirect.wrap_s = stage.wrap_s
            tev_indirect.wrap_t = stage.wrap_t
            tev_indirect.add_previous_texcoord = stage.add_previous_texcoord
            tev_indirect.use_original_lod = stage.use_original_lod
            tev_indirect.bump_alpha = stage.bump_alpha

        for stage, order in zip(material.indirect_stages, entry.indirect_orders):
            order.texcoord = stage.texcoord
            order.texture = stage.texture

        for stage, texcoord_scale in zip(material.indirect_stages, entry.indirect_texcoord_scales):
            texcoord_scale.scale_s = stage.scale_s
            texcoord_scale.scale_t = stage.scale_t

        entry.indirect_matrices = material.indirect_matrices

        return entry

    @pool_load_method(EnumConverter(uint32, gx.CullMode), values=(gx.CULL_BACK, gx.CULL_FRONT, gx.CULL_NONE))
    def pool_cull_mode(pool, material, entry):
        entry.cull_mode_index = pool[material.cull_mode]

    @pool_load_method(uint8)
    def pool_channel_count(pool, material, entry):
        entry.channel_count_index = pool[material.channel_count]

    @pool_load_method(Color)
    def pool_material_color(pool, material, entry):
        for i, channel in enumerate(material.channels):
            entry.material_color_indices[i] = pool[channel.material_color]

    @pool_load_method(Color)
    def pool_ambient_color(pool, material, entry):
        for i, channel in enumerate(material.channels):
            entry.ambient_color_indices[i] = pool[channel.ambient_color]

    @pool_load_method(LightingMode)
    def pool_lighting_mode(pool, material, entry):
        for channel, channel_entry in zip(material.channels, entry.channels):
            channel_entry.color_mode_index = pool[channel.color_mode]
            channel_entry.alpha_mode_index = pool[channel.alpha_mode]

    @pool_load_method(Light)
    def pool_light(pool, material, entry):
        for i, light in enumerate(material.lights):
            if light is None: continue
            entry.light_indices[i] = pool[light]

    @pool_load_method(uint8)
    def pool_texcoord_generator_count(pool, material, entry):
        entry.texcoord_generator_count_index = pool[material.texcoord_generator_count]

    @pool_load_method(TexCoordGenerator)
    def pool_texcoord_generator(pool, material, entry):
        for i, generator in enumerate(material.enabled_texcoord_generators):
            entry.texcoord_generator_indices[i] = pool[generator]

    @pool_load_method(UnknownStruct2)
    def pool_unknown2(pool, material, entry):
        for i, unknown2 in enumerate(material.unknown2):
            if unknown2 is None: continue
            entry.unknown2_indices[i] = pool[unknown2]

    @pool_load_method(TextureMatrix)
    def pool_texture_matrix(pool, material, entry):
        for i, matrix in enumerate(material.texture_matrices):
            if matrix is None: continue
            entry.texture_matrix_indices[i] = pool[matrix]

    @pool_load_method(uint16)
    def pool_texture_index(pool, material, entry):
        for i, index in enumerate(material.texture_indices):
            if index is None: continue
            entry.texture_index_indices[i] = pool[index]

    @pool_load_method(uint8)
    def pool_tev_stage_count(pool, material, entry):
        entry.tev_stage_count_index = pool[material.tev_stage_count]

    @pool_load_method(TevOrder, equal_predicate=TevOrder.__eq__)
    def pool_tev_order(pool, material, entry):
        for i, stage in enumerate(material.enabled_tev_stages):
            entry.tev_order_indices[i] = pool[stage]

    @pool_load_method(TevCombiner, equal_predicate=equal_tev_combiner_and_swap_mode)
    def pool_tev_combiner(pool, material, entry):
        for i, stage in enumerate(material.enabled_tev_stages):
            entry.tev_combiner_indices[i] = pool[stage]

    @pool_load_method(SwapMode, equal_predicate=equal_tev_combiner_and_swap_mode)
    def pool_swap_mode(pool, material, entry):
        for i, stage in enumerate(material.enabled_tev_stages):
            entry.swap_mode_indices[i] = pool[stage]

    @pool_load_method(ColorS16)
    def pool_tev_color(pool, material, entry):
        for i, color in enumerate(material.tev_colors):
            entry.tev_color_indices[i] = pool[color]

        entry.tev_color_previous_index = pool[material.tev_color_previous]

    @pool_load_method(Color)
    def pool_kcolor(pool, material, entry):
        for i, color in enumerate(material.kcolors):
            entry.kcolor_indices[i] = pool[color]

    @pool_load_method(SwapTable)
    def pool_swap_table(pool, material, entry):
        for i, table in enumerate(material.swap_tables):
            entry.swap_table_indices[i] = pool[table]

    @pool_load_method(Fog)
    def pool_fog(pool, material, entry):
        entry.fog_index = pool[material.fog]

    @pool_load_method(AlphaTest)
    def pool_alpha_test(pool, material, entry):
        entry.alpha_test_index = pool[material.alpha_test]

    @pool_load_method(BlendMode)
    def pool_blend_mode(pool, material, entry):
        entry.blend_mode_index = pool[material.blend_mode]

    @pool_load_method(DepthMode)
    def pool_depth_mode(pool, material, entry):
        entry.depth_mode_index = pool[material.depth_mode]

    @pool_load_method(bool8, values=(False, True))
    def pool_depth_test_early(pool, material, entry):
        entry.depth_test_early_index = pool[material.depth_test_early]

    @pool_load_method(bool8, values=(False, True))
    def pool_dither(pool, material, entry):
        entry.dither_index = pool[material.dither]

    @pool_load_method(UnknownStruct5)
    def pool_unknown5(pool, material, entry):
        entry.unknown5_index = pool[material.unknown5]


class SectionUnpacker:

    entry_type = Entry

    def unpack(self, stream):
        base = stream.tell()
        header = Header.unpack(stream)

        materials = [Material() for _ in range(header.material_count)]

        stream.seek(base + header.entry_index_offset)
        entry_indices = [uint16.unpack(stream) for _ in range(header.material_count)]

        entry_count = max(entry_indices) + 1
        stream.seek(base + header.entry_offset)
        entries = [self.entry_type.unpack(stream) for _ in range(entry_count)]
        entries = [entries[i] for i in entry_indices]

        for material, entry in zip(materials, entries):
            material.unknown0 = entry.unknown0
            material.unknown3 = entry.unknown3
            material.unknown4 = entry.unknown4
            self.unload_constant_colors(material, entry)
            self.unload_constant_alphas(material, entry)

        stream.seek(base + header.name_offset)
        names = j3d.string_table.unpack(stream)
        for material, name in zip(materials, names):
            material.name = name

        def unpack_pool(offset, unpack_function): #<-?
            unpack_function(stream, base + offset if offset is not None else None, materials, entries)

        unpack_pool(header.indirect_entry_offset, self.unpack_indirect_entry)

        unpack_pool(header.cull_mode_offset, self.unpack_cull_mode)
        unpack_pool(header.channel_count_offset, self.unpack_channel_count)
        unpack_pool(header.material_color_offset, self.unpack_material_color)
        unpack_pool(header.ambient_color_offset, self.unpack_ambient_color)
        unpack_pool(header.lighting_mode_offset, self.unpack_lighting_mode)
        unpack_pool(header.light_offset, self.unpack_light)
        unpack_pool(header.texcoord_generator_count_offset, self.unpack_texcoord_generator_count)
        unpack_pool(header.texcoord_generator_offset, self.unpack_texcoord_generator)
        unpack_pool(header.unknown2_offset, self.unpack_unknown2)
        unpack_pool(header.texture_matrix_offset, self.unpack_texture_matrix)
        unpack_pool(header.texture_index_offset, self.unpack_texture_index)
        unpack_pool(header.tev_stage_count_offset, self.unpack_tev_stage_count)
        unpack_pool(header.tev_order_offset, self.unpack_tev_order)
        unpack_pool(header.tev_combiner_offset, self.unpack_tev_combiner)
        unpack_pool(header.swap_mode_offset, self.unpack_swap_mode)
        unpack_pool(header.tev_color_offset, self.unpack_tev_color)
        unpack_pool(header.kcolor_offset, self.unpack_kcolor)
        unpack_pool(header.swap_table_offset, self.unpack_swap_table)
        unpack_pool(header.fog_offset, self.unpack_fog)
        unpack_pool(header.alpha_test_offset, self.unpack_alpha_test)
        unpack_pool(header.blend_mode_offset, self.unpack_blend_mode)
        unpack_pool(header.depth_mode_offset, self.unpack_depth_mode)
        unpack_pool(header.depth_test_early_offset, self.unpack_depth_test_early)
        unpack_pool(header.dither_offset, self.unpack_dither)
        unpack_pool(header.unknown5_offset, self.unpack_unknown5)

        stream.seek(base + header.section_size)
        return materials

    def unload_constant_colors(self, material, entry):
        for stage, constant_color in zip(material.tev_stages, entry.constant_colors):
            stage.constant_color = constant_color

    def unload_constant_alphas(self, material, entry):
        for stage, constant_alpha in zip(material.tev_stages, entry.constant_alphas):
            stage.constant_alpha = constant_alpha

    def unpack_indirect_entry(self, stream, offset, materials, entries):
        stream.seek(offset)
        for material in materials:
            self.unload_indirect_entry(material, IndirectEntry.unpack(stream))

    def unload_indirect_entry(self, material, entry):
        material.indirect_stage_count = entry.unknown0

        for tev_stage, tev_indirect in zip(material.tev_stages, entry.tev_indirects):
            tev_stage.indirect_stage = tev_indirect.indirect_stage
            tev_stage.indirect_format = tev_indirect.indirect_format
            tev_stage.indirect_bias_components = tev_indirect.indirect_bias_components
            tev_stage.indirect_matrix = tev_indirect.indirect_matrix
            tev_stage.wrap_s = tev_indirect.wrap_s
            tev_stage.wrap_t = tev_indirect.wrap_t
            tev_stage.add_previous_texcoord = tev_indirect.add_previous_texcoord
            tev_stage.use_original_lod = tev_indirect.use_original_lod
            tev_stage.bump_alpha = tev_indirect.bump_alpha

        for indirect_stage, indirect_order in zip(material.indirect_stages, entry.indirect_orders):
            indirect_stage.texcoord = indirect_order.texcoord
            indirect_stage.texture = indirect_order.texture

        for indirect_stage, indirect_texcoord_scale in zip(material.indirect_stages, entry.indirect_texcoord_scales):
            indirect_stage.scale_s = indirect_texcoord_scale.scale_s
            indirect_stage.scale_t = indirect_texcoord_scale.scale_t

        material.indirect_matrices = entry.indirect_matrices

    @pool_unload_method(EnumConverter(uint32, gx.CullMode))
    def unpack_cull_mode(array, material, entry):
        material.cull_mode = array[entry.cull_mode_index]

    @pool_unload_method(uint8)
    def unpack_channel_count(array, material, entry):
        material.channel_count = array[entry.channel_count_index]

    @pool_unload_method(Color)
    def unpack_material_color(array, material, entry):
        for channel, index in zip(material.channels, entry.material_color_indices):
            channel.material_color = array[index]

    @pool_unload_method(Color)
    def unpack_ambient_color(array, material, entry):
        for channel, index in zip(material.channels, entry.ambient_color_indices):
            channel.ambient_color = array[index]

    @pool_unload_method(LightingMode)
    def unpack_lighting_mode(array, material, entry):
        for channel, channel_entry in zip(material.channels, entry.channels):
            channel.color_mode = array[channel_entry.color_mode_index]
            channel.alpha_mode = array[channel_entry.alpha_mode_index]

    @pool_unload_method(Light)
    def unpack_light(array, material, entry):
        for i, index in enumerate(entry.light_indices):
            if index is None: continue
            material.lights[i] = array[index]

    @pool_unload_method(uint8)
    def unpack_texcoord_generator_count(array, material, entry):
        material.texcoord_generator_count = array[entry.texcoord_generator_count_index]

    @pool_unload_method(TexCoordGenerator)
    def unpack_texcoord_generator(array, material, entry):
        for i in range(material.texcoord_generator_count):
            material.texcoord_generators[i] = array[entry.texcoord_generator_indices[i]]

    @pool_unload_method(UnknownStruct2)
    def unpack_unknown2(array, material, entry):
        for i, index in enumerate(entry.unknown2_indices):
            if index is None: continue
            material.unknown2[i] = array[index]

    @pool_unload_method(TextureMatrix)
    def unpack_texture_matrix(array, material, entry):
        for i, index in enumerate(entry.texture_matrix_indices):
            if index is None: continue
            material.texture_matrices[i] = array[index]

    @pool_unload_method(uint16)
    def unpack_texture_index(array, material, entry):
        for i, index in enumerate(entry.texture_index_indices):
            if index is None: continue
            material.texture_indices[i] = array[index]

    @pool_unload_method(uint8)
    def unpack_tev_stage_count(array, material, entry):
        material.tev_stage_count = array[entry.tev_stage_count_index]

    @pool_unload_method(TevOrder)
    def unpack_tev_order(array, material, entry):
        for stage, index in zip(material.enabled_tev_stages, entry.tev_order_indices):
            tev_order = array[index]
            stage.texcoord = tev_order.texcoord
            stage.texture = tev_order.texture
            stage.color = tev_order.color

    @pool_unload_method(TevCombiner)
    def unpack_tev_combiner(array, material, entry):
        for stage, index in zip(material.enabled_tev_stages, entry.tev_combiner_indices):
            tev_combiner = array[index]
            stage.unknown0 = tev_combiner.unknown0
            stage.color_mode = tev_combiner.color_mode
            stage.alpha_mode = tev_combiner.alpha_mode
            stage.unknown1 = tev_combiner.unknown1

    @pool_unload_method(SwapMode)
    def unpack_swap_mode(array, material, entry):
        for stage, index in zip(material.enabled_tev_stages, entry.swap_mode_indices):
            swap_mode = array[index]
            stage.color_swap_table = swap_mode.color_swap_table
            stage.texture_swap_table = swap_mode.texture_swap_table

    @pool_unload_method(ColorS16)
    def unpack_tev_color(array, material, entry):
        for i, index in enumerate(entry.tev_color_indices):
            material.tev_colors[i] = array[index]

        material.tev_color_previous = array[entry.tev_color_previous_index]

    @pool_unload_method(Color)
    def unpack_kcolor(array, material, entry):
        for i, index in enumerate(entry.kcolor_indices):
            material.kcolors[i] = array[index]

    @pool_unload_method(SwapTable)
    def unpack_swap_table(array, material, entry):
        for i, index in enumerate(entry.swap_table_indices):
            material.swap_tables[i] = array[index]

    @pool_unload_method(Fog)
    def unpack_fog(array, material, entry):
        material.fog = array[entry.fog_index]

    @pool_unload_method(AlphaTest)
    def unpack_alpha_test(array, material, entry):
        material.alpha_test = array[entry.alpha_test_index]

    @pool_unload_method(BlendMode)
    def unpack_blend_mode(array, material, entry):
        material.blend_mode = array[entry.blend_mode_index]

    @pool_unload_method(DepthMode)
    def unpack_depth_mode(array, material, entry):
        material.depth_mode = array[entry.depth_mode_index]

    @pool_unload_method(bool8)
    def unpack_depth_test_early(array, material, entry):
        material.depth_test_early = array[entry.depth_test_early_index]

    @pool_unload_method(bool8)
    def unpack_dither(array, material, entry):
        material.dither = array[entry.dither_index]

    @pool_unload_method(UnknownStruct5)
    def unpack_unknown5(array, material, entry):
        material.unknown5 = array[entry.unknown5_index]


class AmbientSourceSVR0:

    @staticmethod
    def pack(stream, value):
        uint8.pack(stream, 0xFF)

    @staticmethod
    def unpack(stream):
        if uint8.unpack(stream) != 0xFF:
            raise FormatError('invalid ambient source for SVR0')
        return gx.SRC_REG

    @staticmethod
    def sizeof():
        return uint8.sizeof()


class ConstantColorSVR0:

    @staticmethod
    def pack(stream, value):
        uint8.pack(stream, value if value is not None else 0xFF)

    @staticmethod
    def unpack(stream):
        value = uint8.unpack(stream)
        return gx.ConstantColor(value) if value != 0xFF else gx.TEV_KCSEL_1

    @staticmethod
    def sizeof():
        return uint8.sizeof()


class ConstantAlphaSVR0:

    @staticmethod
    def pack(stream, value):
        uint8.pack(stream, value if value is not None else 0xFF)

    @staticmethod
    def unpack(stream):
        value = uint8.unpack(stream)
        return gx.ConstantAlpha(value) if value != 0xFF else gx.TEV_KASEL_1

    @staticmethod
    def sizeof():
        return uint8.sizeof()


class LightingModeSVR0(LightingMode, replace_fields=True):
    ambient_source = AmbientSourceSVR0


class EntrySVR0(Entry, replace_fields=True):
    constant_colors = Array(ConstantColorSVR0, 16)
    constant_alphas = Array(ConstantAlphaSVR0, 16)

    def __init__(self):
        super().__init__()
        self.kcolor_indices = [0, 1, 2, 3]
        self.constant_colors = [None]*16
        self.constant_alphas = [None]*16

    @classmethod
    def unpack(cls, stream):
        entry = super().unpack(stream)

        if entry.ambient_color_indices != [None]*2:
            raise FormatError('invalid ambient color indices for SVR0')
        if entry.light_indices != [None]*8:
            raise FormatError('invalid light indices for SVR0')
        if entry.unknown2_indices != [None]*8:
            raise FormatError('invalid unknown2 indices for SVR0')
        if entry.texture_matrix_indices != [None]*10:
            raise FormatError('invalid texture matrix indices for SVR0')
        if entry.swap_mode_indices != [None]*16:
            raise FormatError('invalid swap mode indices for SVR0')
        if entry.tev_color_indices != [None]*3:
            raise FormatError('invalid tev color indices for SVR0')
        if entry.tev_color_previous_index is not None:
            raise FormatError('invalid tev color previous index for SVR0')
        if entry.kcolor_indices != [0, 1, 2, 3]:
            raise FormatError('invalid kcolor indices for SVR0')
        if entry.swap_table_indices != [None]*4:
            raise FormatError('invalid swap table indices for SVR0')
        if entry.fog_index is not None:
            raise FormatError('invalid fog index  for SVR0')
        if entry.dither_index is not None:
            raise FormatError('invalid dither index for SVR0')
        if entry.unknown5_index is not None:
            raise FormatError('invalid unknown5 index for SVR0')

        if entry.unknown3 != [0xFFFF]*20:
            logger.warning('unknown3 different from default for SVR0')

        return entry


class SectionPackerSVR0(SectionPacker):

    entry_type = EntrySVR0

    def load_constant_colors(self, material, entry):
        for i, stage in enumerate(material.enabled_tev_stages):
            entry.constant_colors[i] = stage.constant_color

    def load_constant_alphas(self, material, entry):
        for i, stage in enumerate(material.enabled_tev_stages):
            entry.constant_alphas[i] = stage.constant_alpha

    def create_indirect_entries(self, materials):
        return None

    def pool_ambient_color(self, materials, entries):
        return None

    def pool_light(self, materials, entries):
        return None

    def pool_unknown2(self, materials, entries):
        return None

    def pool_texture_matrix(self, materials, entries):
        return None

    def pool_swap_mode(self, materials, entries):
        return None

    def pool_tev_color(self, materials, entries):
        return None

    def pool_swap_table(self, materials, entries):
        return None

    def pool_fog(self, materials, entries):
        return None

    def pool_dither(self, materials, entries):
        return None

    def pool_unknown5(self, materials, entries):
        return None

    @pool_load_method(TevCombiner, equal_predicate=TevCombiner.__eq__)
    def pool_tev_combiner(pool, material, entry):
        for i, stage in enumerate(material.enabled_tev_stages):
            entry.tev_combiner_indices[i] = pool[stage]

    @pool_load_method(EnumConverter(uint32, gx.CullMode))
    def pool_cull_mode(pool, material, entry):
        entry.cull_mode_index = pool[material.cull_mode]

    @pool_load_method(Color)
    def pool_material_color(pool, material, entry):
        for i, channel in enumerate(material.enabled_channels):
            entry.material_color_indices[i] = pool[channel.material_color]

    @pool_load_method(LightingModeSVR0)
    def pool_lighting_mode(pool, material, entry):
        for channel, channel_entry in zip(material.enabled_channels, entry.channels):
            channel_entry.color_mode_index = pool[channel.color_mode]
            channel_entry.alpha_mode_index = pool[channel.alpha_mode]

    def pool_kcolor(self, materials, entries):
        return Pool(Color, values=(Color(0xFF, 0xFF, 0xFF, 0xFF),)*4)

    @pool_load_method(bool8)
    def pool_depth_test_early(pool, material, entry):
        entry.depth_test_early_index = pool[material.depth_test_early]


class SectionUnpackerSVR0(SectionUnpacker):

    entry_type = EntrySVR0

    def unpack_indirect_entry(self, stream, offset, materials, entries):
        if offset is not None:
            raise FormatError('invalid indirect entry offset for SVR0')

    def unpack_ambient_color(self, stream, offset, materials, entries):
        if offset is not None:
            raise FormatError('invalid ambient color offset for SVR0')

    def unpack_light(self, stream, offset, materials, entries):
        if offset is not None:
            raise FormatError('invalid light offset for SVR0')

    def unpack_unknown2(self, stream, offset, materials, entries):
        if offset is not None:
            raise FormatError('invalid unknown2 offset for SVR0')

    def unpack_texture_matrix(self, stream, offset, materials, entries):
        if offset is not None:
            raise FormatError('invalid texture matrix offset for SVR0')

    def unpack_swap_mode(self, stream, offset, material, entries):
        if offset is not None:
            raise FormatError('invalid swap mode offset for SVR0')

    def unpack_tev_color(self, stream, offset, material, entries):
        if offset is not None:
            raise FormatError('invalid tev color offset for SVR0')

    def unpack_swap_table(self, stream, offset, material, entries):
        if offset is not None:
            raise FormatError('invalid swap table offset for SVR0')

    def unpack_fog(self, stream, offset, material, entries):
        if offset is not None:
            raise FormatError('invalid fog offset for SVR0')

    def unpack_dither(self, stream, offset, material, entries):
        if offset is not None:
            raise FormatError('invalid dither offset for SVR0')

    def unpack_unknown5(self, stream, offset, material, entries):
        if offset is not None:
            raise FormatError('invalid unknown5 offset for SVR0')

    @pool_unload_method(Color)
    def unpack_material_color(array, material, entry):
        for channel, index in zip(material.enabled_channels, entry.material_color_indices):
            channel.material_color = array[index]

    @pool_unload_method(LightingModeSVR0)
    def unpack_lighting_mode(array, material, entry):
        for channel, channel_entry in zip(material.enabled_channels, entry.channels):
            channel.color_mode = array[channel_entry.color_mode_index]
            channel.alpha_mode = array[channel_entry.alpha_mode_index]

    def unpack_kcolor(self, stream, offset, materials, entries):
        stream.seek(offset)
        for _ in range(4):
            if Color.unpack(stream) != Color(0xFF, 0xFF, 0xFF, 0xFF):
                raise FormatError('invalid kcolor for SVR0')


def pack(stream, materials, subversion):
    if subversion == b'SVR3':
        packer = SectionPacker()
    elif subversion == b'\xFF\xFF\xFF\xFF':
        packer = SectionPackerSVR0()
    else:
        raise ValueError('invalid subversion')

    packer.pack(stream, materials)


def unpack(stream, subversion):
    if subversion == b'SVR3':
        unpacker = SectionUnpacker()
    elif subversion == b'\xFF\xFF\xFF\xFF':
        unpacker = SectionUnpackerSVR0()
    else:
        raise FormatError('invalid subversion')

    return unpacker.unpack(stream)

