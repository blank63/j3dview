import logging
from math import cos, sin, radians
import numpy
from btypes.big_endian import *
import gx
import j3d.string_table


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
            raise FormatError(f'invalid magic: {header.magic}')
        if header.unknown3_offset is not None:
            logger.warning('unexpected unknown3_offset value %s', header.unknown3_offset)
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
    # Ambient source is 0xFF in SVR0 files
    ambient_source = EnumConverter(uint8, gx.ChannelSource, default=gx.SRC_REG)
    __padding__ = Padding(2)

    def __init__(self):
        self.light_enable = False
        self.material_source = gx.SRC_REG
        self.ambient_source = gx.SRC_REG
        self.light_mask = 0
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
        R = numpy.matrix([[c, -s, 0], [s, c, 0], [0, 0, 1]])
        S = numpy.matrix([[self.scale_s, 0, 0], [0, self.scale_t, 0], [0, 0, 1]])
        C = numpy.matrix([[1, 0, self.center_s], [0, 1, self.center_t], [0, 0, 1]])
        T = numpy.matrix([[1, 0, self.translation_s], [0, 1, self.translation_t], [0, 0, 1]])

        # Only types 0x00, 0x06, 0x07, 0x08 and 0x09 have been tested
        if self.matrix_type in {0x00, 0x02, 0x0A, 0x0B, 0x80}:
            P = numpy.matrix([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1]])
        elif self.matrix_type == 0x06:
            P = numpy.matrix([[0.5, 0, 0, 0.5], [0, -0.5, 0, 0.5], [0, 0, 0, 1]])
        elif self.matrix_type == 0x07:
            P = numpy.matrix([[0.5, 0, 0.5, 0], [0, -0.5, 0.5, 0], [0, 0, 1, 0]])
        elif self.matrix_type in {0x08, 0x09}:
            P = numpy.matrix([[0.5, 0, 0.5, 0], [0, -0.5, 0.5, 0], [0, 0, 1, 0]])*numpy.matrix(self.projection_matrix)
        else:
            logger.warning('unknown texture matrix type: %s', self.matrix_type)
            P = numpy.matrix([[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 0, 1]])

        M = T*C*S*R*C.I*P

        if self.shape == gx.TG_MTX2x4:
            return M[:2, :]
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
            logger.warning('unexpected unknown0 value: %s', tev_combiner.unknown0)
        if tev_combiner.unknown1 != 0xFF:
            logger.warning('unexpected unknown1 value: %s', tev_combiner.unknown1)
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
            logger.warning('unexpected unknown2 value')
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
            logger.warning('unexpected unknown5 value')
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
        self.texture_matrices = [TextureMatrix() for _ in range(10)]
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
    # Constant color and constant alpha can be 0xFF in SVR0 files
    constant_colors = Array(EnumConverter(uint8, gx.ConstantColor, default=gx.TEV_KCSEL_1), 16)
    constant_alphas = Array(EnumConverter(uint8, gx.ConstantAlpha, default=gx.TEV_KASEL_1), 16)
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
        entry = super().unpack(stream)
        if entry.unknown0 != entry.unknown1 or entry.unknown0 not in {0, 1}:
            logger.warning('unexpected unknown0 and unknown1 values: %s, %s', entry.unknown0, entry.unknown1)
        return entry


class Indexer:

    def __init__(self):
        self.keys = []

    def __getitem__(self, key):
        for i, k in enumerate(self.keys):
            if self.equal_predicate(key, k):
                return i
        self.keys.append(key)
        return len(self.keys) - 1

    def __iter__(self):
        yield from self.keys

    def update(self, keys):
        for key in keys:
            self[key]

    @staticmethod
    def equal_predicate(a, b):
        return a == b


class ArrayUnpacker:

    def __init__(self, stream, offset, element_type):
        self.stream = stream
        self.offset = offset
        self.element_type = element_type

    def __getitem__(self, index):
        self.stream.seek(self.offset + index*self.element_type.sizeof())
        return self.element_type.unpack(self.stream)


def load_cull_mode_array(materials, entries):
    indexer = Indexer()
    indexer.update([gx.CULL_BACK, gx.CULL_FRONT, gx.CULL_NONE])
    for material, entry in zip(materials, entries):
        entry.cull_mode_index = indexer[material.cull_mode]
    return indexer


def unload_cull_mode_array(materials, entries, array):
    for material, entry in zip(materials, entries):
        if entry.cull_mode_index is not None:
            material.cull_mode = array[entry.cull_mode_index]


def load_channel_count_array(materials, entries):
    indexer = Indexer()
    for material, entry in zip(materials, entries):
        entry.channel_count_index = indexer[material.channel_count]
    return indexer


def unload_channel_count_array(materials, entries, array):
    for material, entry in zip(materials, entries):
        if entry.channel_count_index is not None:
            material.channel_count = array[entry.channel_count_index]


def load_material_color_array(materials, entries):
    indexer = Indexer()
    for material, entry in zip(materials, entries):
        for i, channel in enumerate(material.channels):
            entry.material_color_indices[i] = indexer[channel.material_color]
    return indexer


def unload_material_color_array(materials, entries, array):
    for material, entry in zip(materials, entries):
        for channel, index in zip(material.channels, entry.material_color_indices):
            if index is not None:
                channel.material_color = array[index]


def load_ambient_color_array(materials, entries):
    indexer = Indexer()
    for material, entry in zip(materials, entries):
        for i, channel in enumerate(material.channels):
            entry.ambient_color_indices[i] = indexer[channel.ambient_color]
    return indexer


def unload_ambient_color_array(materials, entries, array):
    for material, entry in zip(materials, entries):
        for channel, index in zip(material.channels, entry.ambient_color_indices):
            if index is not None:
                channel.ambient_color = array[index]


def load_lighting_mode_array(materials, entries):
    indexer = Indexer()
    for material, entry in zip(materials, entries):
        for channel, channel_entry in zip(material.channels, entry.channels):
            channel_entry.color_mode_index = indexer[channel.color_mode]
            channel_entry.alpha_mode_index = indexer[channel.alpha_mode]
    return indexer


def unload_lighting_mode_array(materials, entries, array):
    for material, entry in zip(materials, entries):
        for channel, channel_entry in zip(material.channels, entry.channels):
            if channel_entry.color_mode_index is not None:
                channel.color_mode = array[channel_entry.color_mode_index]
            if channel_entry.alpha_mode_index is not None:
                channel.alpha_mode = array[channel_entry.alpha_mode_index]


def load_light_array(materials, entries):
    indexer = Indexer()
    for material, entries in zip(materials, entries):
        for i, light in enumerate(material.lights):
            if light is not None:
                entry.light_indices[i] = indexer[light]
    return indexer


def unload_light_array(materials, entries, array):
    for material, entry in zip(materials, entries):
        for i, index in enumerate(entry.light_indices):
            if index is not None:
                material.lights[i] = array[index]


def load_texcoord_generator_count_array(materials, entries):
    indexer = Indexer()
    for material, entry in zip(materials, entries):
        entry.texcoord_generator_count_index = indexer[material.texcoord_generator_count]
    return indexer


def unload_texcoord_generator_count_array(materials, entries, array):
    for material, entry in zip(materials, entries):
        if entry.texcoord_generator_count_index is not None:
            material.texcoord_generator_count = array[entry.texcoord_generator_count_index]


def load_texcoord_generator_array(materials, entries):
    indexer = Indexer()
    for material, entry in zip(materials, entries):
        for i, generator in enumerate(material.enabled_texcoord_generators):
            entry.texcoord_generator_indices[i] = indexer[generator]
    return indexer


def unload_texcoord_generator_array(materials, entries, array):
    for material, entry in zip(materials, entries):
        for i, index in enumerate(entry.texcoord_generator_indices):
            if index is not None:
                material.texcoord_generators[i] = array[index]


def load_unknown2_array(materials, entries):
    indexer = Indexer()
    for material, entries in zip(materials, entries):
        for i, unknown2 in enumerate(material.unknown2):
            if unknown2 is not None:
                entry.unknown2_indices[i] = indexer[unknown2]
    return indexer


def unload_unknown2_array(materials, entries, array):
    for material, entry in zip(materials, entries):
        for i, index in enumerate(entry.unknown2_indices):
            if index is not None:
                material.unknown2[i] = array[index]


def load_texture_matrix_array(materials, entries):
    indexer = Indexer()
    for material, entry in zip(materials, entries):
        # Nintendo seems to pair up texture matrices with texcoord generators
        # in order, and a matrix is included in the MAT3 section even if it
        # is not used by the generator. We want to stay as close to what
        # Nintendo does, but also allow users to assign arbitrary texture
        # matrices to texcoord generators.
        use_matrix = [False]*10
        for generator in material.enabled_texcoord_generators:
            if generator.matrix != gx.IDENTITY:
                use_matrix[gx.TEXMTX.index(generator.matrix)] = True
        for i, matrix in enumerate(material.texture_matrices):
            if i < material.texcoord_generator_count or use_matrix[i]:
                entry.texture_matrix_indices[i] = indexer[matrix]
    return indexer


def unload_texture_matrix_array(materials, entries, array):
    for material, entry in zip(materials, entries):
        for i, index in enumerate(entry.texture_matrix_indices):
            if index is not None:
                material.texture_matrices[i] = array[index]


def load_texture_index_array(materials, entries):
    indexer = Indexer()
    for material, entry in zip(materials, entries):
        for i, index in enumerate(material.texture_indices):
            if index is not None:
                entry.texture_index_indices[i] = indexer[index]
    return indexer


def unload_texture_index_array(materials, entries, array):
    for material, entry in zip(materials, entries):
        for i, index in enumerate(entry.texture_index_indices):
            if index is not None:
                material.texture_indices[i] = array[index]


def load_tev_stage_count_array(materials, entries):
    indexer = Indexer()
    for material, entry in zip(materials, entries):
        entry.tev_stage_count_index = indexer[material.tev_stage_count]
    return indexer


def unload_tev_stage_count_array(materials, entries, array):
    for material, entry in zip(materials, entries):
        if entry.tev_stage_count_index is not None:
            material.tev_stage_count = array[entry.tev_stage_count_index]


def load_tev_order_array(materials, entries):
    indexer = Indexer()
    indexer.equal_predicate = TevOrder.__eq__
    for material, entry in zip(materials, entries):
        for i, stage in enumerate(material.enabled_tev_stages):
            entry.tev_order_indices[i] = indexer[stage]
    return indexer


def unload_tev_order_array(materials, entries, array):
    for material, entry in zip(materials, entries):
        for stage, index in zip(material.tev_stages, entry.tev_order_indices):
            if index is not None:
                order = array[index]
                stage.texcoord = order.texcoord
                stage.texture = order.texture
                stage.color = order.color


def equal_tev_combiner_and_swap_mode(a, b):
    return TevCombiner.__eq__(a, b) and SwapMode.__eq__(a, b)


def load_tev_combiner_array(materials, entries):
    indexer = Indexer()
    # It looks like tev combiner and swap mode are indexed together for some reason
    indexer.equal_predicate = equal_tev_combiner_and_swap_mode
    for material, entry in zip(materials, entries):
        for i, stage in enumerate(material.enabled_tev_stages):
            entry.tev_combiner_indices[i] = indexer[stage]
    return indexer


def unload_tev_combiner_array(materials, entries, array):
    for material, entry in zip(materials, entries):
        for stage, index in zip(material.tev_stages, entry.tev_combiner_indices):
            if index is not None:
                combiner = array[index]
                stage.unknown0 = combiner.unknown0
                stage.color_mode = combiner.color_mode
                stage.alpha_mode = combiner.alpha_mode
                stage.unknown1 = combiner.unknown1


def load_swap_mode_array(materials, entries):
    indexer = Indexer()
    # It looks like tev combiner and swap mode are indexed together for some reason
    indexer.equal_predicate = equal_tev_combiner_and_swap_mode
    for material, entry in zip(materials, entries):
        for i, stage in enumerate(material.enabled_tev_stages):
            entry.swap_mode_indices[i] = indexer[stage]
    return indexer


def unload_swap_mode_array(materials, entries, array):
    for material, entry in zip(materials, entries):
        for stage, index in zip(material.tev_stages, entry.swap_mode_indices):
            if index is not None:
                swap_mode = array[index]
                stage.color_swap_table = swap_mode.color_swap_table
                stage.texture_swap_table = swap_mode.texture_swap_table


def load_tev_color_array(materials, entries):
    indexer = Indexer()
    for material, entry in zip(materials, entries):
        for i, color in enumerate(material.tev_colors):
            entry.tev_color_indices[i] = indexer[color]
        entry.tev_color_previous_index = indexer[material.tev_color_previous]
    return indexer


def unload_tev_color_array(materials, entries, array):
    for material, entry in zip(materials, entries):
        for i, index in enumerate(entry.tev_color_indices):
            if index is not None:
                material.tev_colors[i] = array[index]
        if entry.tev_color_previous_index is not None:
            material.tev_color_previous = array[entry.tev_color_previous_index]


def load_kcolor_array(materials, entries):
    indexer = Indexer()
    for material, entry in zip(materials, entries):
        for i, color in enumerate(material.kcolors):
            entry.kcolor_indices[i] = indexer[color]
    return indexer


def unload_kcolor_array(materials, entries, array):
    for material, entry in zip(materials, entries):
        for i, index in enumerate(entry.kcolor_indices):
            if index is not None:
                material.kcolors[i] = array[index]


def load_swap_table_array(materials, entries):
    indexer = Indexer()
    for material, entry in zip(materials, entries):
        for i, table in enumerate(material.swap_tables):
            entry.swap_table_indices[i] = indexer[table]
    return indexer


def unload_swap_table_array(materials, entries, array):
    for material, entry in zip(materials, entries):
        for i, index in enumerate(entry.swap_table_indices):
            if index is not None:
                material.swap_tables[i] = array[index]


def load_fog_array(materials, entries):
    indexer = Indexer()
    for material, entry in zip(materials, entries):
        entry.fog_index = indexer[material.fog]
    return indexer


def unload_fog_array(materials, entries, array):
    for material, entry in zip(materials, entries):
        if entry.fog_index is not None:
            material.fog = array[entry.fog_index]


def load_alpha_test_array(materials, entries):
    indexer = Indexer()
    for material, entry in zip(materials, entries):
        entry.alpha_test_index = indexer[material.alpha_test]
    return indexer


def unload_alpha_test_array(materials, entries, array):
    for material, entry in zip(materials, entries):
        if entry.alpha_test_index is not None:
            material.alpha_test = array[entry.alpha_test_index]


def load_blend_mode_array(materials, entries):
    indexer = Indexer()
    for material, entry in zip(materials, entries):
        entry.blend_mode_index = indexer[material.blend_mode]
    return indexer


def unload_blend_mode_array(materials, entries, array):
    for material, entry in zip(materials, entries):
        if entry.blend_mode_index is not None:
            material.blend_mode = array[entry.blend_mode_index]


def load_depth_mode_array(materials, entries):
    indexer = Indexer()
    for material, entry in zip(materials, entries):
        entry.depth_mode_index = indexer[material.depth_mode]
    return indexer


def unload_depth_mode_array(materials, entries, array):
    for material, entry in zip(materials, entries):
        if entry.depth_mode_index is not None:
            material.depth_mode = array[entry.depth_mode_index]


def load_depth_test_early_array(materials, entries):
    indexer = Indexer()
    indexer.update([False, True])
    for material, entry in zip(materials, entries):
        entry.depth_test_early_index = indexer[material.depth_test_early]
    return indexer


def unload_depth_test_early_array(materials, entries, array):
    for material, entry in zip(materials, entries):
        if entry.depth_test_early_index is not None:
            material.depth_test_early = array[entry.depth_test_early_index]


def load_dither_array(materials, entries):
    indexer = Indexer()
    indexer.update([False, True])
    for material, entry in zip(materials, entries):
        entry.dither_index = indexer[material.dither]
    return indexer


def unload_dither_array(materials, entries, array):
    for material, entry in zip(materials, entries):
        if entry.dither_index is not None:
            material.dither = array[entry.dither_index]


def load_unknown5_array(materials, entries):
    indexer = Indexer()
    for material, entry in zip(materials, entries):
        entry.unknown5_index = indexer[material.unknown5]
    return indexer


def unload_unknown5_array(materials, entries, array):
    for material, entry in zip(materials, entries):
        if entry.unknown5_index is not None:
            material.unknown5 = array[entry.unknown5_index]


def load_indirect_entry(material):
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


def unload_indirect_entry(material, entry):
    material.indirect_stage_count = entry.unknown0

    for stage, tev_indirect in zip(material.tev_stages, entry.tev_indirects):
        stage.indirect_stage = tev_indirect.indirect_stage
        stage.indirect_format = tev_indirect.indirect_format
        stage.indirect_bias_components = tev_indirect.indirect_bias_components
        stage.indirect_matrix = tev_indirect.indirect_matrix
        stage.wrap_s = tev_indirect.wrap_s
        stage.wrap_t = tev_indirect.wrap_t
        stage.add_previous_texcoord = tev_indirect.add_previous_texcoord
        stage.use_original_lod = tev_indirect.use_original_lod
        stage.bump_alpha = tev_indirect.bump_alpha

    for stage, order in zip(material.indirect_stages, entry.indirect_orders):
        stage.texcoord = order.texcoord
        stage.texture = order.texture

    for stage, texcoord_scale in zip(material.indirect_stages, entry.indirect_texcoord_scales):
        stage.scale_s = texcoord_scale.scale_s
        stage.scale_t = texcoord_scale.scale_t

    material.indirect_matrices = entry.indirect_matrices


def pack(stream, materials):
    entries = [Entry() for _ in materials]

    for material, entry in zip(materials, entries):
        for i, stage in enumerate(material.tev_stages):
            entry.constant_colors[i] = stage.constant_color
            entry.constant_alphas[i] = stage.constant_alpha
        entry.unknown0 = material.unknown0
        entry.unknown3 = material.unknown3
        entry.unknown4 = material.unknown4

    def _l(load_function):
        return load_function(materials, entries)

    cull_mode_array = _l(load_cull_mode_array)
    channel_count_array = _l(load_channel_count_array)
    material_color_array = _l(load_material_color_array)
    ambient_color_array = _l(load_ambient_color_array)
    lighting_mode_array = _l(load_lighting_mode_array)
    light_array = _l(load_light_array)
    texcoord_generator_count_array = _l(load_texcoord_generator_count_array)
    texcoord_generator_array = _l(load_texcoord_generator_array)
    unknown2_array = _l(load_unknown2_array)
    texture_matrix_array = _l(load_texture_matrix_array)
    texture_index_array = _l(load_texture_index_array)
    tev_stage_count_array = _l(load_tev_stage_count_array)
    tev_order_array = _l(load_tev_order_array)
    tev_combiner_array = _l(load_tev_combiner_array)
    swap_mode_array = _l(load_swap_mode_array)
    tev_color_array = _l(load_tev_color_array)
    kcolor_array = _l(load_kcolor_array)
    swap_table_array = _l(load_swap_table_array)
    fog_array = _l(load_fog_array)
    alpha_test_array = _l(load_alpha_test_array)
    blend_mode_array = _l(load_blend_mode_array)
    depth_mode_array = _l(load_depth_mode_array)
    depth_test_early_array = _l(load_depth_test_early_array)
    dither_array = _l(load_dither_array)
    unknown5_array = _l(load_unknown5_array)

    entry_indexer = Indexer()
    entry_indices = [entry_indexer[entry] for entry in entries]

    base = stream.tell()
    header = Header()
    header.material_count = len(materials)
    stream.write(b'\x00'*Header.sizeof())

    header.entry_offset = stream.tell() - base
    for entry in entry_indexer:
        Entry.pack(stream, entry)

    header.entry_index_offset = stream.tell() - base
    for index in entry_indices:
        uint16.pack(stream, index)

    align(stream, 4)
    header.name_offset = stream.tell() - base
    j3d.string_table.pack(stream, (material.name for material in materials))

    align(stream, 4)
    header.indirect_entry_offset = stream.tell() - base
    for material in materials:
        indirect_entry = load_indirect_entry(material)
        IndirectEntry.pack(stream, indirect_entry)

    def _p(array, element_type):
        offset = stream.tell() - base
        for element in array:
            element_type.pack(stream, element)
        return offset

    align(stream, 4)
    header.cull_mode_offset = _p(cull_mode_array, EnumConverter(uint32, gx.CullMode))
    header.material_color_offset = _p(material_color_array, Color)
    header.channel_count_offset = _p(channel_count_array, uint8)
    align(stream, 4)
    header.lighting_mode_offset = _p(lighting_mode_array, LightingMode)
    header.ambient_color_offset = _p(ambient_color_array, Color)
    header.light_offset = _p(light_array, Light)
    header.texcoord_generator_count_offset = _p(texcoord_generator_count_array, uint8)
    align(stream, 4)
    header.texcoord_generator_offset = _p(texcoord_generator_array, TexCoordGenerator)
    header.unknown2_offset = _p(unknown2_array, UnknownStruct2)
    header.texture_matrix_offset = _p(texture_matrix_array, TextureMatrix)
    header.texture_index_offset = _p(texture_index_array, uint16)
    align(stream, 4)
    header.tev_order_offset = _p(tev_order_array, TevOrder)
    header.tev_color_offset = _p(tev_color_array, ColorS16)
    header.kcolor_offset = _p(kcolor_array, Color)
    header.tev_stage_count_offset = _p(tev_stage_count_array, uint8)
    align(stream, 4)
    header.tev_combiner_offset = _p(tev_combiner_array, TevCombiner)
    header.swap_mode_offset = _p(swap_mode_array, SwapMode)
    header.swap_table_offset = _p(swap_table_array, SwapTable)
    header.fog_offset = _p(fog_array, Fog)
    header.alpha_test_offset = _p(alpha_test_array, AlphaTest)
    header.blend_mode_offset = _p(blend_mode_array, BlendMode)
    header.depth_mode_offset = _p(depth_mode_array, DepthMode)
    header.depth_test_early_offset = _p(depth_test_early_array, bool8)
    align(stream, 4)
    header.dither_offset = _p(dither_array, bool8)
    align(stream, 4)
    header.unknown5_offset = _p(unknown5_array, UnknownStruct5)

    align(stream, 0x20)
    header.section_size = stream.tell() - base
    stream.seek(base)
    Header.pack(stream, header)
    stream.seek(base + header.section_size)


def unpack(stream):
    base = stream.tell()
    header = Header.unpack(stream)

    materials = [Material() for _ in range(header.material_count)]

    stream.seek(base + header.entry_index_offset)
    entry_indices = [uint16.unpack(stream) for _ in range(header.material_count)]

    entry_count = max(entry_indices) + 1
    stream.seek(base + header.entry_offset)
    entries = [Entry.unpack(stream) for _ in range(entry_count)]
    entries = [entries[i] for i in entry_indices]

    for material, entry in zip(materials, entries):
        for i, stage in enumerate(material.tev_stages):
            stage.constant_color = entry.constant_colors[i]
            stage.constant_alpha = entry.constant_alphas[i]
        material.unknown0 = entry.unknown0
        material.unknown3 = entry.unknown3
        material.unknown4 = entry.unknown4

    stream.seek(base + header.name_offset)
    names = j3d.string_table.unpack(stream)
    for material, name in zip(materials, names):
        material.name = name

    if header.indirect_entry_offset is not None:
        stream.seek(base + header.indirect_entry_offset)
        for material in materials:
            indirect_entry = IndirectEntry.unpack(stream)
            unload_indirect_entry(material, indirect_entry)

    def _u(offset, unload_function, element_type):
        if offset is None:
            array = None
        else:
            array = ArrayUnpacker(stream, base + offset, element_type)
        unload_function(materials, entries, array)

    _u(header.cull_mode_offset, unload_cull_mode_array, EnumConverter(uint32, gx.CullMode))
    _u(header.channel_count_offset, unload_channel_count_array, uint8)
    _u(header.material_color_offset, unload_material_color_array, Color)
    _u(header.ambient_color_offset, unload_ambient_color_array, Color)
    _u(header.lighting_mode_offset, unload_lighting_mode_array, LightingMode)
    _u(header.light_offset, unload_light_array, Light)
    _u(header.texcoord_generator_count_offset, unload_texcoord_generator_count_array, uint8)
    _u(header.texcoord_generator_offset, unload_texcoord_generator_array, TexCoordGenerator)
    _u(header.unknown2_offset, unload_unknown2_array, UnknownStruct2)
    _u(header.texture_matrix_offset, unload_texture_matrix_array, TextureMatrix)
    _u(header.texture_index_offset, unload_texture_index_array, uint16)
    _u(header.tev_stage_count_offset, unload_tev_stage_count_array, uint8)
    _u(header.tev_order_offset, unload_tev_order_array, TevOrder)
    _u(header.tev_combiner_offset, unload_tev_combiner_array, TevCombiner)
    _u(header.swap_mode_offset, unload_swap_mode_array, SwapMode)
    _u(header.tev_color_offset, unload_tev_color_array, ColorS16)
    _u(header.kcolor_offset, unload_kcolor_array, Color)
    _u(header.swap_table_offset, unload_swap_table_array, SwapTable)
    _u(header.fog_offset, unload_fog_array, Fog)
    _u(header.alpha_test_offset, unload_alpha_test_array, AlphaTest)
    _u(header.blend_mode_offset, unload_blend_mode_array, BlendMode)
    _u(header.depth_mode_offset, unload_depth_mode_array, DepthMode)
    _u(header.depth_test_early_offset, unload_depth_test_early_array, bool8)
    _u(header.dither_offset, unload_dither_array, bool8)
    _u(header.unknown5_offset, unload_unknown5_array, UnknownStruct5)

    stream.seek(base + header.section_size)
    return materials

