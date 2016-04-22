import functools
from btypes.big_endian import *
import gx
from j3d.material import *
import j3d.string_table

import logging
logger = logging.getLogger(__name__)

index8 = NoneableConverter(uint8,0xFF)
index16 = NoneableConverter(uint16,0xFFFF)


class Header(Struct):
    magic = ByteString(4)
    section_size = uint32
    material_count = uint16
    __padding__ = Padding(2)
    entry_offset = uint32
    entry_index_offset = uint32
    name_offset = uint32
    indirect_entry_offset = uint32
    cull_mode_offset = uint32
    material_color_offset = uint32
    channel_count_offset = uint32
    lighting_mode_offset = uint32
    ambient_color_offset = uint32
    light_offset = uint32
    texcoord_generator_count_offset = uint32
    texcoord_generator_offset = uint32
    unknown2_offset = uint32
    texture_matrix_offset = uint32
    unknown3_offset = uint32
    texture_index_offset = uint32
    tev_order_offset = uint32
    tev_color_offset = uint32
    kcolor_offset = uint32
    tev_stage_count_offset = uint32
    tev_combiner_offset = uint32
    swap_mode_offset = uint32
    swap_table_offset = uint32
    fog_offset = uint32
    alpha_test_offset = uint32
    blend_mode_offset = uint32
    depth_mode_offset = uint32
    depth_test_early_offset = uint32
    dither_offset = uint32
    unknown5_offset = uint32

    def __init__(self):
        self.magic = b'MAT3'
        self.unknown2_offset = 0
        self.unknown3_offset = 0

    @classmethod
    def unpack(cls,stream):
        header = super().unpack(stream)
        if header.magic != b'MAT3':
            raise FormatError('invalid magic')
        if header.unknown2_offset != 0:
            logger.warning('unknown2_offset different from default')
        if header.unknown3_offset != 0:
            logger.warning('unknown3_offset different from default')
        return header


class ColorS16(Color,replace_fields=True):
    r = sint16
    g = sint16
    b = sint16
    a = sint16


class TevCombiner(Struct):
    unknown0 = uint8
    color_mode = TevColorMode
    alpha_mode = TevAlphaMode
    unknown1 = uint8
    
    @classmethod
    def unpack(cls,stream):
        tev_combiner = super().unpack(stream)
        if tev_combiner.unknown0 != 0xFF:
            logger.warning('tev combiner unknown0 different from default')
        if tev_combiner.unknown1 != 0xFF:
            logger.warning('tev combiner unknown1 different from default')
        return tev_combiner


class TevOrder(Struct):
    """Arguments to GXSetTevOrder."""
    texcoord = EnumConverter(uint8,gx.TexCoord)
    texture = EnumConverter(uint8,gx.Texture)
    color = EnumConverter(uint8,gx.Channel)
    __padding__ = Padding(1)


class SwapMode(Struct):
    """Arguments to GXSetTevSwapMode."""
    color_swap_table = EnumConverter(uint8,gx.SwapTable)
    texture_swap_table = EnumConverter(uint8,gx.SwapTable)
    __padding__ = Padding(2)


class TevIndirect(Struct):
    """Arguments to GXSetTevIndirect."""
    indirect_stage = EnumConverter(uint8,gx.IndirectStage)
    indirect_format = EnumConverter(uint8,gx.IndirectFormat)
    indirect_bias_components = EnumConverter(uint8,gx.IndirectBiasComponents)
    indirect_matrix = EnumConverter(uint8,gx.IndirectMatrix)
    wrap_s = EnumConverter(uint8,gx.IndirectWrap)
    wrap_t = EnumConverter(uint8,gx.IndirectWrap)
    add_previous_texcoord = bool8
    use_original_lod = bool8
    bump_alpha = EnumConverter(uint8,gx.IndirectBumpAlpha)
    __padding__ = Padding(3)


class IndirectOrder(Struct):
    """Arguments to GXSetIndTexOrder."""
    texcoord = EnumConverter(uint8,gx.TexCoord)
    texture = EnumConverter(uint8,gx.Texture)
    __padding__ = Padding(2)


class IndirectTexCoordScale(Struct):
    """Arguments to GXSetIndTexCoordScale."""
    scale_s = EnumConverter(uint8,gx.IndirectScale)
    scale_t = EnumConverter(uint8,gx.IndirectScale)
    __padding__ = Padding(2)
        
        
class ChannelEntry(Struct):
    color_mode_index = index16
    alpha_mode_index = index16

    def __init__(self):
        self.color_mode_index = None
        self.alpha_mode_index = None


class Entry(Struct):
    unknown0 = uint8
    cull_mode_index = index8
    channel_count_index = index8
    texcoord_generator_count_index = index8
    tev_stage_count_index = index8
    depth_test_early_index = index8
    depth_mode_index = index8
    dither_index = index8
    material_color_indices = Array(index16,2)
    channels = Array(ChannelEntry,2)
    ambient_color_indices = Array(index16,2)
    light_indices = Array(index16,8)
    texcoord_generator_indices = Array(index16,8)
    unknown2 = Array(uint16,8)
    texture_matrix_indices = Array(index16,10)
    unknown3 = Array(uint16,20)
    texture_index_indices = Array(index16,8)
    kcolor_indices = Array(index16,4)
    constant_colors = Array(EnumConverter(uint8,gx.ConstantColor),16)
    constant_alphas = Array(EnumConverter(uint8,gx.ConstantAlpha),16)
    tev_order_indices = Array(index16,16)
    tev_color_indices = Array(index16,3)
    tev_color_previous_index = index16
    tev_combiner_indices = Array(index16,16)
    swap_mode_indices = Array(index16,16)
    swap_table_indices = Array(index16,4)
    unknown4 = Array(uint16,12)
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
        self.unknown2 = [0xFFFF]*8
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
    
    @classmethod
    def unpack(cls,stream):
        entry = super().unpack(stream)
        if entry.unknown2 != [0xFFFF]*8:
            logger.warning('unknown2 different from default')
        return entry

    def load_constant_colors(self,material):
        for i,stage in enumerate(material.tev_stages):
            self.constant_colors[i] = stage.constant_color

    def load_constant_alphas(self,material):
        for i,stage in enumerate(material.tev_stages):
            self.constant_alphas[i] = stage.constant_alpha

    def unload_constant_colors(self,material):
        for stage,constant_color in zip(material.tev_stages,self.constant_colors):
            stage.constant_color = constant_color

    def unload_constant_alphas(self,material):
        for stage,constant_alpha in zip(material.tev_stages,self.constant_alphas):
            stage.constant_alpha = constant_alpha


        
class IndirectEntry(Struct):
    unknown0 = uint8 # enable or indirect stage count?
    unknown1 = uint8 # enable or indirect stage count?
    __padding__ = Padding(2)
    indirect_orders = Array(IndirectOrder,4)
    indirect_matrices = Array(IndirectMatrix,3)
    indirect_texcoord_scales = Array(IndirectTexCoordScale,4)
    tev_indirects = Array(TevIndirect,16)

    def __init__(self):
        self.tev_indirects = [TevIndirect() for _ in range(16)]
        self.indirect_orders = [IndirectOrder() for _ in range(4)]
        self.indirect_texcoord_scales = [IndirectTexCoordScale() for _ in range(4)]
        self.indirect_matrices = [IndirectMatrix() for _ in range(3)]

    @classmethod
    def unpack(cls,stream):
        indirect_entry = super().unpack(stream)
        if indirect_entry.unknown0 != indirect_entry.unknown1 or indirect_entry.unknown0 not in {0,1}:
            raise FormatError('unsuported indirect texture entry unknown0 and unknown1')
        return indirect_entry

    def load(self,material):
        self.unknown0 = material.indirect_stage_count
        self.unknown1 = material.indirect_stage_count

        for stage,tev_indirect in zip(material.tev_stages,self.tev_indirects):
            tev_indirect.indirect_stage = stage.indirect_stage
            tev_indirect.indirect_format = stage.indirect_format
            tev_indirect.indirect_bias_components = stage.indirect_bias_components
            tev_indirect.indirect_matrix = stage.indirect_matrix
            tev_indirect.wrap_s = stage.wrap_s
            tev_indirect.wrap_t = stage.wrap_t
            tev_indirect.add_previous_texcoord = stage.add_previous_texcoord
            tev_indirect.use_original_lod = stage.use_original_lod
            tev_indirect.bump_alpha = stage.bump_alpha

        for stage,order in zip(material.indirect_stages,self.indirect_orders):
            order.texcoord = stage.texcoord
            order.texture = stage.texture

        for stage,texcoord_scale in zip(material.indirect_stages,self.indirect_texcoord_scales):
            texcoord_scale.scale_s = stage.scale_s
            texcoord_scale.scale_t = stage.scale_t

        self.indirect_matrices = material.indirect_matrices

    def unload(self,material):
        material.indirect_stage_count = self.unknown0

        for tev_stage,tev_indirect in zip(material.tev_stages,self.tev_indirects):
            tev_stage.indirect_stage = tev_indirect.indirect_stage
            tev_stage.indirect_format = tev_indirect.indirect_format
            tev_stage.indirect_bias_components = tev_indirect.indirect_bias_components
            tev_stage.indirect_matrix = tev_indirect.indirect_matrix
            tev_stage.wrap_s = tev_indirect.wrap_s
            tev_stage.wrap_t = tev_indirect.wrap_t
            tev_stage.add_previous_texcoord = tev_indirect.add_previous_texcoord
            tev_stage.use_original_lod = tev_indirect.use_original_lod
            tev_stage.bump_alpha = tev_indirect.bump_alpha

        for stage,order in zip(material.indirect_stages,self.indirect_orders):
            stage.texcoord = order.texcoord
            stage.texture = order.texture

        for stage,texcoord_scale in zip(material.indirect_stages,self.indirect_texcoord_scales):
            stage.scale_s = texcoord_scale.scale_s
            stage.scale_t = texcoord_scale.scale_t

        material.indirect_matrices = self.indirect_matrices
            
    
class Pool:

    def __init__(self,element_type,values=tuple(),equal_predicate=None):
        self.element_type = element_type
        self.values = list(values)
        if equal_predicate is not None:
            self.equal_predicate = equal_predicate

    def __getitem__(self,value):
        for i in range(len(self.values)):
            if self.equal_predicate(value,self.values[i]):
                return i

        self.values.append(value)
        return len(self.values) - 1

    def __iter__(self):
        yield from self.values

    @staticmethod
    def equal_predicate(a,b):
        return a == b


class ArrayUnpacker:

    def __init__(self,stream,offset,element_type):
        self.stream = stream
        self.offset = offset
        self.element_type = element_type

    def __getitem__(self,index):
        self.stream.seek(self.offset + index*self.element_type.sizeof())
        return self.element_type.unpack(self.stream)


def partial_call(func):
    def wrapper(*args,**kwargs):
        return functools.partial(func,*args,**kwargs)
    return wrapper


@partial_call
def pool_loader(element_type,load_function,**kwargs):
    @functools.wraps(load_function)
    def wrapper(self,materials,entries):
        pool = Pool(element_type,**kwargs)
        for material,entry in zip(materials,entries):
            load_function(pool,material,entry)
        return pool
    return wrapper


@partial_call
def array_unloader(element_type,unload_function):
    @functools.wraps(unload_function)
    def wrapper(self,offset,materials,entries):
        array = self.create_array(offset,element_type)
        for material,entry in zip(materials,entries):
            unload_function(array,material,entry)
    return wrapper


def equal_tev_combiner_and_swap_mode(a,b):
    return TevCombiner.__eq__(a,b) and SwapMode.__eq__(a,b)


class SectionPacker:

    entry_type = Entry

    def seek(self,offset):
        self.stream.seek(self.base + offset)

    def tell(self):
        return self.stream.tell() - self.base

    def pack(self,stream,materials):
        self.stream = stream
        self.base = stream.tell()

        entries = [self.entry_type() for _ in range(len(materials))]

        for material,entry in zip(materials,entries):
            entry.unknown0 = material.unknown0
            entry.unknown2 = material.unknown2
            entry.unknown3 = material.unknown3
            entry.unknown4 = material.unknown4
            entry.load_constant_colors(material)
            entry.load_constant_alphas(material)

        cull_mode_pool = self.pool_cull_mode(materials,entries)
        channel_count_pool = self.pool_channel_count(materials,entries)
        material_color_pool = self.pool_material_color(materials,entries)
        ambient_color_pool = self.pool_ambient_color(materials,entries)
        lighting_mode_pool = self.pool_lighting_mode(materials,entries)
        light_pool = self.pool_light(materials,entries)
        texcoord_generator_count_pool = self.pool_texcoord_generator_count(materials,entries)
        texcoord_generator_pool = self.pool_texcoord_generator(materials,entries)
        texture_matrix_pool = self.pool_texture_matrix(materials,entries)
        texture_index_pool = self.pool_texture_index(materials,entries)
        tev_stage_count_pool = self.pool_tev_stage_count(materials,entries)
        tev_order_pool = self.pool_tev_order(materials,entries)
        tev_combiner_pool = self.pool_tev_combiner(materials,entries)
        swap_mode_pool = self.pool_swap_mode(materials,entries)
        tev_color_pool = self.pool_tev_color(materials,entries)
        kcolor_pool = self.pool_kcolor(materials,entries)
        swap_table_pool = self.pool_swap_table(materials,entries)
        fog_pool = self.pool_fog(materials,entries)
        alpha_test_pool = self.pool_alpha_test(materials,entries)
        blend_mode_pool = self.pool_blend_mode(materials,entries)
        depth_mode_pool = self.pool_depth_mode(materials,entries)
        depth_test_early_pool = self.pool_depth_test_early(materials,entries)
        dither_pool = self.pool_dither(materials,entries)
        unknown5_pool = self.pool_unknown5(materials,entries)

        entry_pool = Pool(self.entry_type)
        entry_indices = [entry_pool[entry] for entry in entries]

        header = Header()
        header.material_count = len(materials)
        stream.write(b'\x00'*Header.sizeof())

        header.entry_offset = self.pack_pool(entry_pool)

        header.entry_index_offset = self.tell()
        for index in entry_indices:
            uint16.pack(stream,index)

        align(stream,4)
        header.name_offset = self.tell()
        j3d.string_table.pack(stream,(material.name for material in materials))

        align(stream,4)
        header.indirect_entry_offset = self.pack_indirect_entries(materials)

        align(stream,4)
        header.cull_mode_offset = self.pack_pool(cull_mode_pool)
        header.material_color_offset = self.pack_pool(material_color_pool)
        header.channel_count_offset = self.pack_pool(channel_count_pool)
        align(stream,4)
        header.lighting_mode_offset = self.pack_pool(lighting_mode_pool)
        header.ambient_color_offset = self.pack_pool(ambient_color_pool)
        header.light_offset = self.pack_pool(light_pool)
        header.texcoord_generator_count_offset = self.pack_pool(texcoord_generator_count_pool)
        align(stream,4)
        header.texcoord_generator_offset = self.pack_pool(texcoord_generator_pool)
        header.texture_matrix_offset = self.pack_pool(texture_matrix_pool)
        header.texture_index_offset = self.pack_pool(texture_index_pool)
        align(stream,4)
        header.tev_order_offset = self.pack_pool(tev_order_pool)
        header.tev_color_offset = self.pack_pool(tev_color_pool)
        header.kcolor_offset = self.pack_pool(kcolor_pool)
        header.tev_stage_count_offset = self.pack_pool(tev_stage_count_pool)
        align(stream,4)
        header.tev_combiner_offset = self.pack_pool(tev_combiner_pool)
        header.swap_mode_offset = self.pack_pool(swap_mode_pool)
        header.swap_table_offset = self.pack_pool(swap_table_pool)
        header.fog_offset = self.pack_pool(fog_pool)
        header.alpha_test_offset = self.pack_pool(alpha_test_pool)
        header.blend_mode_offset = self.pack_pool(blend_mode_pool)
        header.depth_mode_offset = self.pack_pool(depth_mode_pool)
        header.depth_test_early_offset = self.pack_pool(depth_test_early_pool)
        align(stream,4)
        header.dither_offset = self.pack_pool(dither_pool)
        align(stream,4)
        header.unknown5_offset = self.pack_pool(unknown5_pool)

        align(stream,0x20)
        header.section_size = self.tell()
        self.seek(0)
        Header.pack(stream,header)
        self.seek(header.section_size)

    def pack_indirect_entries(self,materials):
        offset = self.tell()
        for material in materials:
            indirect_entry = IndirectEntry()
            indirect_entry.load(material)
            IndirectEntry.pack(self.stream,indirect_entry)
        return offset

    def pack_pool(self,pool):
        if pool is None: return 0
        offset = self.tell()
        for value in pool:
            pool.element_type.pack(self.stream,value)
        return offset

    @pool_loader(EnumConverter(uint32,gx.CullMode),values=(gx.CULL_BACK,gx.CULL_FRONT,gx.CULL_NONE))
    def pool_cull_mode(pool,material,entry):
        entry.cull_mode_index = pool[material.cull_mode]

    @pool_loader(uint8)
    def pool_channel_count(pool,material,entry):
        entry.channel_count_index = pool[material.channel_count]

    @pool_loader(Color)
    def pool_material_color(pool,material,entry):
        for i,channel in enumerate(material.channels):
            entry.material_color_indices[i] = pool[channel.material_color]

    @pool_loader(Color)
    def pool_ambient_color(pool,material,entry):
        for i,channel in enumerate(material.channels):
            entry.ambient_color_indices[i] = pool[channel.ambient_color]

    @pool_loader(LightingMode)
    def pool_lighting_mode(pool,material,entry):
        for channel,channel_entry in zip(material.channels,entry.channels):
            channel_entry.color_mode_index = pool[channel.color_mode]
            channel_entry.alpha_mode_index = pool[channel.alpha_mode]

    @pool_loader(Light)
    def pool_light(pool,material,entry):
        for i,light in enumerate(material.lights):
            if light is None: continue
            entry.light_indices[i] = pool[light]

    @pool_loader(uint8)
    def pool_texcoord_generator_count(pool,material,entry):
        entry.texcoord_generator_count_index = pool[material.texcoord_generator_count]

    @pool_loader(TexCoordGenerator)
    def pool_texcoord_generator(pool,material,entry):
        for i,generator in enumerate(material.enabled_texcoord_generators):
            entry.texcoord_generator_indices[i] = pool[generator]

    @pool_loader(TextureMatrix)
    def pool_texture_matrix(pool,material,entry):
        for i,matrix in enumerate(material.texture_matrices):
            if matrix is None: continue
            entry.texture_matrix_indices[i] = pool[matrix]

    @pool_loader(uint16)
    def pool_texture_index(pool,material,entry):
        for i,index in enumerate(material.texture_indices):
            if index is None: continue
            entry.texture_index_indices[i] = pool[index]

    @pool_loader(uint8)
    def pool_tev_stage_count(pool,material,entry):
        entry.tev_stage_count_index = pool[material.tev_stage_count]

    @pool_loader(TevOrder,equal_predicate=TevOrder.__eq__)
    def pool_tev_order(pool,material,entry):
        for i,stage in enumerate(material.enabled_tev_stages):
            entry.tev_order_indices[i] = pool[stage]

    @pool_loader(TevCombiner,equal_predicate=equal_tev_combiner_and_swap_mode)
    def pool_tev_combiner(pool,material,entry):
        for i,stage in enumerate(material.enabled_tev_stages):
            entry.tev_combiner_indices[i] = pool[stage]

    @pool_loader(SwapMode,equal_predicate=equal_tev_combiner_and_swap_mode)
    def pool_swap_mode(pool,material,entry):
        for i,stage in enumerate(material.enabled_tev_stages):
            entry.swap_mode_indices[i] = pool[stage]

    @pool_loader(ColorS16)
    def pool_tev_color(pool,material,entry):
        for i,color in enumerate(material.tev_colors):
            entry.tev_color_indices[i] = pool[color]

        entry.tev_color_previous_index = pool[material.tev_color_previous]

    @pool_loader(Color)
    def pool_kcolor(pool,material,entry):
        for i,color in enumerate(material.kcolors):
            entry.kcolor_indices[i] = pool[color]

    @pool_loader(SwapTable)
    def pool_swap_table(pool,material,entry):
        for i,table in enumerate(material.swap_tables):
            entry.swap_table_indices[i] = pool[table]

    @pool_loader(Fog)
    def pool_fog(pool,material,entry):
        entry.fog_index = pool[material.fog]

    @pool_loader(AlphaTest)
    def pool_alpha_test(pool,material,entry):
        entry.alpha_test_index = pool[material.alpha_test]

    @pool_loader(BlendMode)
    def pool_blend_mode(pool,material,entry):
        entry.blend_mode_index = pool[material.blend_mode]

    @pool_loader(DepthMode)
    def pool_depth_mode(pool,material,entry):
        entry.depth_mode_index = pool[material.depth_mode]

    @pool_loader(bool8,values=(False,True))
    def pool_depth_test_early(pool,material,entry):
        entry.depth_test_early_index = pool[material.depth_test_early]

    @pool_loader(bool8,values=(False,True))
    def pool_dither(pool,material,entry):
        entry.dither_index = pool[material.dither]

    @pool_loader(UnknownStruct5)
    def pool_unknown5(pool,material,entry):
        entry.unknown5_index = pool[material.unknown5]


class SectionUnpacker:

    entry_type = Entry

    def seek(self,offset):
        self.stream.seek(self.base + offset)

    def unpack(self,stream):
        self.stream = stream
        self.base = stream.tell()

        header = Header.unpack(stream)

        materials = [Material() for _ in range(header.material_count)]

        self.seek(header.entry_index_offset)
        entry_indices = [uint16.unpack(stream) for _ in range(header.material_count)]

        entry_count = max(entry_indices) + 1
        self.seek(header.entry_offset)
        entries = [self.entry_type.unpack(stream) for _ in range(entry_count)]
        entries = [entries[i] for i in entry_indices]

        for material,entry in zip(materials,entries):
            material.unknown0 = entry.unknown0
            material.unknown2 = entry.unknown2
            material.unknown3 = entry.unknown3
            material.unknown4 = entry.unknown4
            entry.unload_constant_colors(material)
            entry.unload_constant_alphas(material)

        self.seek(header.name_offset)
        names = j3d.string_table.unpack(stream)
        for material,name in zip(materials,names):
            material.name = name

        self.unpack_indirect_entries(header.indirect_entry_offset,materials)

        self.unpack_cull_mode(header.cull_mode_offset,materials,entries)
        self.unpack_channel_count(header.channel_count_offset,materials,entries)
        self.unpack_material_color(header.material_color_offset,materials,entries)
        self.unpack_ambient_color(header.ambient_color_offset,materials,entries)
        self.unpack_lighting_mode(header.lighting_mode_offset,materials,entries)
        self.unpack_light(header.light_offset,materials,entries)
        self.unpack_texcoord_generator_count(header.texcoord_generator_count_offset,materials,entries)
        self.unpack_texcoord_generator(header.texcoord_generator_offset,materials,entries)
        self.unpack_texture_matrix(header.texture_matrix_offset,materials,entries)
        self.unpack_texture_index(header.texture_index_offset,materials,entries)
        self.unpack_tev_stage_count(header.tev_stage_count_offset,materials,entries)
        self.unpack_tev_order(header.tev_order_offset,materials,entries)
        self.unpack_tev_combiner(header.tev_combiner_offset,materials,entries)
        self.unpack_swap_mode(header.swap_mode_offset,materials,entries)
        self.unpack_tev_color(header.tev_color_offset,materials,entries)
        self.unpack_kcolor(header.kcolor_offset,materials,entries)
        self.unpack_swap_table(header.swap_table_offset,materials,entries)
        self.unpack_fog(header.fog_offset,materials,entries)
        self.unpack_alpha_test(header.alpha_test_offset,materials,entries)
        self.unpack_blend_mode(header.blend_mode_offset,materials,entries)
        self.unpack_depth_mode(header.depth_mode_offset,materials,entries)
        self.unpack_depth_test_early(header.depth_test_early_offset,materials,entries)
        self.unpack_dither(header.dither_offset,materials,entries)
        self.unpack_unknown5(header.unknown5_offset,materials,entries)

        self.seek(header.section_size)
        return materials

    def unpack_indirect_entries(self,offset,materials):
        self.seek(offset)
        for material in materials:
            indirect_entry = IndirectEntry.unpack(self.stream)
            indirect_entry.unload(material)

    def create_array(self,offset,element_type):
        if offset == 0: return None
        return ArrayUnpacker(self.stream,self.base + offset,element_type)

    @array_unloader(EnumConverter(uint32,gx.CullMode))
    def unpack_cull_mode(array,material,entry):
        material.cull_mode = array[entry.cull_mode_index]

    @array_unloader(uint8)
    def unpack_channel_count(array,material,entry):
        material.channel_count = array[entry.channel_count_index]

    @array_unloader(Color)
    def unpack_material_color(array,material,entry):
        for channel,index in zip(material.channels,entry.material_color_indices):
            channel.material_color = array[index]

    @array_unloader(Color)
    def unpack_ambient_color(array,material,entry):
        for channel,index in zip(material.channels,entry.ambient_color_indices):
            channel.ambient_color = array[index]

    @array_unloader(LightingMode)
    def unpack_lighting_mode(array,material,entry):
        for channel,channel_entry in zip(material.channels,entry.channels):
            channel.color_mode = array[channel_entry.color_mode_index]
            channel.alpha_mode = array[channel_entry.alpha_mode_index]

    @array_unloader(Light)
    def unpack_light(array,material,entry):
        for i,index in enumerate(entry.light_indices):
            if index is None: continue
            material.lights[i] = array[index]

    @array_unloader(uint8)
    def unpack_texcoord_generator_count(array,material,entry):
        material.texcoord_generator_count = array[entry.texcoord_generator_count_index]

    @array_unloader(TexCoordGenerator)
    def unpack_texcoord_generator(array,material,entry):
        for i in range(material.texcoord_generator_count):
            material.texcoord_generators[i] = array[entry.texcoord_generator_indices[i]]

    @array_unloader(TextureMatrix)
    def unpack_texture_matrix(array,material,entry):
        for i,index in enumerate(entry.texture_matrix_indices):
            if index is None: continue
            material.texture_matrices[i] = array[index]

    @array_unloader(uint16)
    def unpack_texture_index(array,material,entry):
        for i,index in enumerate(entry.texture_index_indices):
            if index is None: continue
            material.texture_indices[i] = array[index]

    @array_unloader(uint8)
    def unpack_tev_stage_count(array,material,entry):
        material.tev_stage_count = array[entry.tev_stage_count_index]

    @array_unloader(TevOrder)
    def unpack_tev_order(array,material,entry):
        for stage,index in zip(material.enabled_tev_stages,entry.tev_order_indices):
            tev_order = array[index]
            stage.texcoord = tev_order.texcoord
            stage.texture = tev_order.texture
            stage.color = tev_order.color

    @array_unloader(TevCombiner)
    def unpack_tev_combiner(array,material,entry):
        for stage,index in zip(material.enabled_tev_stages,entry.tev_combiner_indices):
            tev_combiner = array[index]
            stage.unknown0 = tev_combiner.unknown0
            stage.color_mode = tev_combiner.color_mode
            stage.alpha_mode = tev_combiner.alpha_mode
            stage.unknown1 = tev_combiner.unknown1

    @array_unloader(SwapMode)
    def unpack_swap_mode(array,material,entry):
        for stage,index in zip(material.enabled_tev_stages,entry.swap_mode_indices):
            swap_mode = array[index]
            stage.color_swap_table = swap_mode.color_swap_table
            stage.texture_swap_table = swap_mode.texture_swap_table

    @array_unloader(ColorS16)
    def unpack_tev_color(array,material,entry):
        for i,index in enumerate(entry.tev_color_indices):
            material.tev_colors[i] = array[index]

        material.tev_color_previous = array[entry.tev_color_previous_index]

    @array_unloader(Color)
    def unpack_kcolor(array,material,entry):
        for i,index in enumerate(entry.kcolor_indices):
            material.kcolors[i] = array[index]

    @array_unloader(SwapTable)
    def unpack_swap_table(array,material,entry):
        for i,index in enumerate(entry.swap_table_indices):
            material.swap_tables[i] = array[index]

    @array_unloader(Fog)
    def unpack_fog(array,material,entry):
        material.fog = array[entry.fog_index]

    @array_unloader(AlphaTest)
    def unpack_alpha_test(array,material,entry):
        material.alpha_test = array[entry.alpha_test_index]

    @array_unloader(BlendMode)
    def unpack_blend_mode(array,material,entry):
        material.blend_mode = array[entry.blend_mode_index]

    @array_unloader(DepthMode)
    def unpack_depth_mode(array,material,entry):
        material.depth_mode = array[entry.depth_mode_index]

    @array_unloader(bool8)
    def unpack_depth_test_early(array,material,entry):
        material.depth_test_early = array[entry.depth_test_early_index]

    @array_unloader(bool8)
    def unpack_dither(array,material,entry):
        material.dither = array[entry.dither_index]

    @array_unloader(UnknownStruct5)
    def unpack_unknown5(array,material,entry):
        material.unknown5 = array[entry.unknown5_index]


class AmbientSourceSVR0:

    @staticmethod
    def pack(stream,value):
        uint8.pack(stream,0xFF)

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
    def pack(stream,value):
        uint8.pack(stream,value if value is not None else 0xFF)

    @staticmethod
    def unpack(stream):
        value = uint8.unpack(stream)
        return gx.ConstantColor(value) if value != 0xFF else gx.TEV_KCSEL_1

    @staticmethod
    def sizeof():
        return uint8.sizeof()


class ConstantAlphaSVR0:

    @staticmethod
    def pack(stream,value):
        uint8.pack(stream,value if value is not None else 0xFF)

    @staticmethod
    def unpack(stream):
        value = uint8.unpack(stream)
        return gx.ConstantAlpha(value) if value != 0xFF else gx.TEV_KASEL_1

    @staticmethod
    def sizeof():
        return uint8.sizeof()


class LightingModeSVR0(LightingMode,replace_fields=True):
    ambient_source = AmbientSourceSVR0


class EntrySVR0(Entry,replace_fields=True):
    constant_colors = Array(ConstantColorSVR0,16)
    constant_alphas = Array(ConstantAlphaSVR0,16)

    def __init__(self):
        super().__init__()
        self.kcolor_indices = [0,1,2,3]
        self.constant_colors = [None]*16
        self.constant_alphas = [None]*16

    @classmethod
    def unpack(cls,stream):
        entry = super().unpack(stream)

        if entry.ambient_color_indices != [None]*2:
            raise FormatError('invalid ambient color indices for SVR0')
        if entry.light_indices != [None]*8:
            raise FormatError('invalid light indices for SVR0')
        if entry.texture_matrix_indices != [None]*10:
            raise FormatError('invalid texture matrix indices for SVR0')
        if entry.swap_mode_indices != [None]*16:
            raise FormatError('invalid swap mode indices for SVR0')
        if entry.tev_color_indices != [None]*3:
            raise FormatError('invalid tev color indices for SVR0')
        if entry.tev_color_previous_index is not None:
            raise FormatError('invalid tev color previous index for SVR0')
        if entry.kcolor_indices != [0,1,2,3]:
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

    def load_constant_colors(self,material):
        for i,stage in enumerate(material.enabled_tev_stages):
            self.constant_colors[i] = stage.constant_color

    def load_constant_alphas(self,material):
        for i,stage in enumerate(material.enabled_tev_stages):
            self.constant_alphas[i] = stage.constant_alpha


class SectionPackerSVR0(SectionPacker):

    entry_type = EntrySVR0

    def pack_indirect_entries(self,materials):
        return 0

    def pool_ambient_color(self,materials,entries):
        return None

    def pool_light(self,materials,entries):
        return None

    def pool_texture_matrix(self,materials,entries):
        return None

    @pool_loader(TevCombiner,equal_predicate=TevCombiner.__eq__)
    def pool_tev_combiner(pool,material,entry):
        for i,stage in enumerate(material.enabled_tev_stages):
            entry.tev_combiner_indices[i] = pool[stage]

    def pool_swap_mode(self,material,entries):
        return None

    def pool_tev_color(self,material,entries):
        return None

    def pool_swap_table(self,material,entries):
        return None

    def pool_fog(self,material,entries):
        return None

    def pool_dither(self,material,entries):
        return None

    def pool_unknown5(self,material,entries):
        return None

    @pool_loader(EnumConverter(uint32,gx.CullMode))
    def pool_cull_mode(pool,material,entry):
        entry.cull_mode_index = pool[material.cull_mode]

    @pool_loader(Color)
    def pool_material_color(pool,material,entry):
        for i,channel in enumerate(material.enabled_channels):
            entry.material_color_indices[i] = pool[channel.material_color]

    @pool_loader(LightingModeSVR0)
    def pool_lighting_mode(pool,material,entry):
        for channel,channel_entry in zip(material.enabled_channels,entry.channels):
            channel_entry.color_mode_index = pool[channel.color_mode]
            channel_entry.alpha_mode_index = pool[channel.alpha_mode]

    def pool_kcolor(self,materials,entries):
        return Pool(Color,[Color(0xFF,0xFF,0xFF,0xFF)]*4)

    @pool_loader(bool8)
    def pool_depth_test_early(pool,material,entry):
        entry.depth_test_early_index = pool[material.depth_test_early]


class SectionUnpackerSVR0(SectionUnpacker):

    entry_type = EntrySVR0

    def unpack_indirect_entries(self,offset,materials):
        if offset != 0:
            raise FormatError('invalid indirect entry offset for SVR0')

    def unpack_ambient_color(self,offset,materials,entries):
        if offset != 0:
            raise FormatError('invalid ambient color offset for SVR0')

    def unpack_light(self,offset,materials,entries):
        if offset != 0:
            raise FormatError('invalid light offset for SVR0')

    def unpack_texture_matrix(self,offset,materials,entries):
        if offset != 0:
            raise FormatError('invalid texture matrix offset for SVR0')
        assert offset == 0

    def unpack_swap_mode(self,offset,material,entries):
        if offset != 0:
            raise FormatError('invalid swap mode offset for SVR0')

    def unpack_tev_color(self,offset,material,entries):
        if offset != 0:
            raise FormatError('invalid tev color offset for SVR0')

    def unpack_swap_table(self,offset,material,entries):
        if offset != 0:
            raise FormatError('invalid swap table offset for SVR0')

    def unpack_fog(self,offset,material,entries):
        if offset != 0:
            raise FormatError('invalid fog offset for SVR0')

    def unpack_dither(self,offset,material,entries):
        if offset != 0:
            raise FormatError('invalid dither offset for SVR0')

    def unpack_unknown5(self,offset,material,entries):
        if offset != 0:
            raise FormatError('invalid unknown5 offset for SVR0')

    @array_unloader(Color)
    def unpack_material_color(array,material,entry):
        for channel,index in zip(material.enabled_channels,entry.material_color_indices):
            channel.material_color = array[index]

    @array_unloader(LightingModeSVR0)
    def unpack_lighting_mode(array,material,entry):
        for channel,channel_entry in zip(material.enabled_channels,entry.channels):
            channel.color_mode = array[channel_entry.color_mode_index]
            channel.alpha_mode = array[channel_entry.alpha_mode_index]

    def unpack_kcolor(self,offset,materials,entries):
        array = self.create_array(offset,Color)
        for i in range(4):
            if array[i] != Color(0xFF,0xFF,0xFF,0xFF):
                raise FormatError('invalid kcolor for SVR0')


def pack(stream,materials,subversion):
    if subversion == b'SVR3':
        packer = SectionPacker()
    elif subversion == b'\xFF\xFF\xFF\xFF':
        packer = SectionPackerSVR0()
    else:
        raise ValueError('invalid subversion')

    packer.pack(stream,materials)


def unpack(stream,subversion):
    if subversion == b'SVR3':
        unpacker = SectionUnpacker()
    elif subversion == b'\xFF\xFF\xFF\xFF':
        unpacker = SectionUnpackerSVR0()
    else:
        raise ValueError('invalid subversion')

    return unpacker.unpack(stream)

