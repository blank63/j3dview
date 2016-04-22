from math import log,floor,ceil,frexp
from btypes.big_endian import *
import gx
import j3d.string_table


class Header(Struct):
    magic = ByteString(4)
    section_size = uint32
    packet_count = uint16
    __padding__ = Padding(2)
    packet_offset = uint32
    subpacket_location_offset = uint32
    matrix_index_offset = uint32
    unknown0_offset = uint32
    index_offset = uint32
    name_offset = uint32

    def __init__(self):
        self.magic = b'MDL3'


class PacketLocation(Struct):
    offset = uint32
    size = uint32


class SubpacketLocation(Struct):
    channel_color_offset = uint16
    channel_offset = uint16
    texcoord_generator_offset = uint16
    texture_offset = uint16
    tev_offset = uint16
    fog_offset = uint16
    __padding__ = Padding(4)


class BitField:

    def __init__(self,value=0):
        self.value = value

    def __index__(self):
        return self.value

    def __int__(self):
        return self.value

    def __eq__(self,other):
        return self.value == int(other)

    def __setitem__(self,key,value):
        if isinstance(key,slice):
            mask = ~(-1 << (key.stop - key.start)) << key.start
            self.value = (self.value & ~mask) | ((value << key.start) & mask)
        else:
            if value:
                self.value |= 1 << key
            else:
                self.value &= ~(1 << key)


class BPCommand(BitField):

    def __init__(self,register,value=0):
        super().__init__(register << 24 | value)

    @property
    def register(self):
        return self.value >> 24

    @staticmethod
    def pack(stream,command):
        uint8.pack(stream,0x61)
        uint32.pack(stream,command.value)


class BPMask(BPCommand):

    def __init__(self,mask):
        super().__init__(0xFE,mask)


class XFCommand(list):

    def __init__(self,register,values=tuple(),element_type=uint32):
        super().__init__(values)
        self.register = register
        self.element_type = element_type

    def __getitem__(self,key):
        if isinstance(key,slice):
            return XFCommand(self.register,super().__getitem__(key),self.element_type)
        else:
            return super().__getitem__(key)

    @staticmethod
    def pack(stream,command):
        if not command: return
        uint8.pack(stream,0x10)
        uint16.pack(stream,len(command) - 1)
        uint16.pack(stream,command.register)
        for value in command:
            command.element_type.pack(stream,value)


def convert_cull_mode(mode):
    if mode == gx.CULL_NONE:
        return 0
    if mode == gx.CULL_FRONT:
        return 2
    if mode == gx.CULL_BACK:
        return 1
    if mode == gx.CULL_ALL:
        return 3

    raise ValueError('invalid cull mode')


def convert_rasterized_color(color):
    if color in {gx.COLOR0,gx.ALPHA0,gx.COLOR0A0}:
        return 0
    if color in {gx.COLOR1,gx.ALPHA1,gx.COLOR1A1}:
        return 1
    if color == gx.COLOR_ZERO:
        return 7
    if color == gx.ALPHA_BUMP:
        return 5
    if color == gx.ALPHA_BUMPN:
        return 6
    if color == gx.COLOR_NULL:
        return 7

    raise ValueError('invalid rasterized color')


def convert_texcoord_source(source):
    if source == gx.TG_POS:
        return 0
    if source == gx.TG_NRM:
        return 1
    if source == gx.TG_BINRM:
        return 3
    if source == gx.TG_TANGENT:
        return 4
    if source in gx.TG_TEX:
        return source + 1
    if source in gx.TG_TEXCOORD:
        return 5
    if source in gx.TG_COLOR:
        return 2

    raise ValueError('invalid texture coordinate generator source')


def convert_minification_filter(mode):
    if mode == gx.NEAR:
        return 0
    if mode == gx.LINEAR:
        return 4
    if mode == gx.NEAR_MIP_NEAR:
        return 1
    if mode == gx.LIN_MIP_NEAR:
        return 5
    if mode == gx.NEAR_MIP_LIN:
        return 2
    if mode == gx.LIN_MIP_LIN:
        return 6

    raise ValueError('invalid minification filter')


class Packet:

    def __init__(self,material,textures):
        self.init_commands()

        self.use_texture = [False]*8
        self.use_texture_matrix = [False]*10

        for generator in material.enabled_texcoord_generators:
            if generator.matrix != gx.IDENTITY:
                self.use_texture_matrix[generator.matrix.index] = True

        for stage in material.enabled_tev_stages:
            if stage.texture != gx.TEXMAP_NULL:
                self.SetTexCoordScale(stage.texcoord.index,textures[material.texture_indices[stage.texture.index]])
                self.use_texture[stage.texture.index] = True

        for stage in material.enabled_indirect_stages:
            self.SetTexCoordScale(stage.texcoord.index,textures[material.texture_indices[stage.texture.index]])
            self.SetTextureIndirect(stage.texture.index)
            self.use_texture[stage.texture.index] = True

        self.SetCullMode(material.cull_mode)

        self.SetNumChans(material.channel_count)

        for i,channel in enumerate(material.channels):
            self.SetChanMatColor(i,channel.material_color)
            self.SetChanAmbColor(i,channel.ambient_color)
            self.SetChanCtrl(gx.COLOR[i],channel.color_mode)
            self.SetChanCtrl(gx.ALPHA[i],channel.alpha_mode)

        for i,light in enumerate(material.lights):
            if light is None: continue
            self.SetLight(i,light)

        self.SetNumTexGens(material.texcoord_generator_count)

        for i,generator in enumerate(material.texcoord_generators):
            self.SetTexCoordGen(i,generator)

        for i,matrix in enumerate(material.texture_matrices):
            if not self.use_texture_matrix[i]: continue
            self.SetTexMatrix(i,matrix)

        for i,texture_index in enumerate(material.texture_indices):
            if not self.use_texture[i]: continue
            self.SetTexture(i,texture_index,textures[texture_index])

        self.SetNumTevStages(material.tev_stage_count)

        for i,stage in enumerate(material.tev_stages):
            self.SetTevOrder(i,stage)
            self.SetTevColorIn(i,stage.color_mode)
            self.SetTevColorOp(i,stage.color_mode)
            self.SetTevAlphaIn(i,stage.alpha_mode)
            self.SetTevAlphaOp(i,stage.alpha_mode)
            self.SetTevKColorSel(i,stage.constant_color)
            self.SetTevKAlphaSel(i,stage.constant_alpha)
            self.SetTevSwapMode(i,stage)
            self.SetTevIndirect(i,stage)

        for i,color in enumerate(material.tev_colors):
            self.SetTevColor(gx.TEVREG[i],color)

        self.SetTevColor(gx.TEVPREV,material.tev_color_previous)

        for i,color in enumerate(material.kcolors):
            self.SetTevKColor(i,color)

        for i,table in enumerate(material.swap_tables):
            self.SetTevSwapModeTable(i,table)

        self.SetNumIndStages(material.indirect_stage_count)

        for i,stage in enumerate(material.indirect_stages):
            self.SetIndTexOrder(i,stage)
            self.SetIndTexCoordScale(i,stage)

        for i,matrix in enumerate(material.indirect_matrices):
            self.SetIndTexMatrix(i,matrix)

        self.SetAlphaCompare(material.alpha_test)
        self.SetFog(material.fog)
        self.SetZCompLoc(material.depth_test_early)
        self.SetZMode(material.depth_mode)
        self.SetFogRangeAdj(material.fog)
        self.SetBlendMode(material.blend_mode)
        self.SetDither(material.dither)

    def init_commands(self):
        self.tx_setmode0 = [BPCommand(reg) for reg in (0x80,0x81,0x82,0x83,0xA0,0xA1,0xA2,0xA3)]
        self.tx_setmode1 = [BPCommand(reg) for reg in (0x84,0x85,0x86,0x87,0xA4,0xA5,0xA6,0xA7)]
        self.tx_setimage0 = [BPCommand(reg) for reg in (0x88,0x89,0x8A,0x8B,0xA8,0xA9,0xAA,0xAB)]
        self.tx_setimage3 = [BPCommand(reg) for reg in (0x94,0x95,0x96,0x97,0xB4,0xB5,0xB6,0xB7)]
        self.loadtlut0 = [BPCommand(0x64) for _ in range(8)]
        self.loadtlut1 = [BPCommand(0x65) for _ in range(8)]
        self.tx_settlut = [BPCommand(reg) for reg in (0x98,0x99,0x9A,0x9B,0xB8,0xB9,0xBA,0xBB)]
        self.tref = [BPCommand(0x28 + i) for i in range(8)]
        self.su_ssize = [BPCommand(0x30 + 2*i) for i in range(8)]
        self.su_tsize = [BPCommand(0x31 + 2*i) for i in range(8)]

        self.tev_color_ra = [BPCommand(0xE0 + 2*i) for i in range(4)]
        self.tev_color_bg = [BPCommand(0xE1 + 2*i) for i in range(4)]
        self.kcolor_ra = [BPCommand(0xE0 + 2*i,1 << 23) for i in range(4)]
        self.kcolor_bg = [BPCommand(0xE1 + 2*i,1 << 23) for i in range(4)]
        self.tev_color_env = [BPCommand(0xC0 + 2*i) for i in range(16)]
        self.tev_alpha_env = [BPCommand(0xC1 + 2*i) for i in range(16)]
        self.ind_cmd = [BPCommand(0x10 + i) for i in range(16)]
        self.tev_ksel = [BPCommand(0xF6 + i) for i in range(8)]

        self.ind_mtxa = [BPCommand(0x06 + 3*i) for i in range(3)]
        self.ind_mtxb = [BPCommand(0x07 + 3*i) for i in range(3)]
        self.ind_mtxc = [BPCommand(0x08 + 3*i) for i in range(3)]
        self.ras1_ss = [BPCommand(0x25 + i) for i in range(2)]
        self.iref = BPCommand(0x27,0xFFFFFF)
        self.ind_imask = BPCommand(0x0F)

        self.fog_param0 = BPCommand(0xEE)
        self.fog_param1 = BPCommand(0xEF)
        self.fog_param2 = BPCommand(0xF0)
        self.fog_param3 = BPCommand(0xF1)
        self.fog_color = BPCommand(0xF2)
        self.fog_table = [BPCommand(0xE9 + i) for i in range(5)]
        self.fog_range = BPCommand(0xE8)

        self.alphacompare = BPCommand(0xF3)
        self.blendmode = BPCommand(0x41)
        self.zmode = BPCommand(0x40)
        self.zcompare = BPCommand(0x43)
        self.genmode = BPCommand(0x00)

        self.texmtx = [XFCommand(0x0078 + 12*i,element_type=float32) for i in range(10)]
        self.texcoordgen0 = XFCommand(0x1040,[BitField() for _ in range(8)])
        self.texcoordgen1 = XFCommand(0x1050,[BitField() for _ in range(8)])
        self.matcolor = XFCommand(0x100C,[BitField() for _ in range(2)])
        self.ambcolor = XFCommand(0x100A,[BitField() for _ in range(2)])
        self.chanctrl = XFCommand(0x100E,[BitField() for _ in range(4)])

        self.light_color = [XFCommand(0x0603 + 13*i,[BitField()]) for i in range(8)]
        self.light_attn = [XFCommand(0x0604 + 13*i,[0,0,0,0,0,0],element_type=float32) for i in range(8)]
        self.light_pos = [XFCommand(0x060A + 13*i,[0,0,0],element_type=float32) for i in range(8)]
        self.light_dir = [XFCommand(0x060D + 13*i,[0,0,0],element_type=float32) for i in range(8)]

        self.numchans = XFCommand(0x1009,[0])
        self.numtexgens = XFCommand(0x103F,[0])

        self.mtxidx = [BitField(0x3CF3CF00),BitField(0x00F3CF3C)] # CP 0x30,0x40

    def SetNumChans(self,count):
        self.genmode[4:7] = count
        self.numchans[0] = count

    def SetChanCtrl(self,i,mode):
        self.chanctrl[i][0:1] = mode.material_source
        self.chanctrl[i][1] = mode.light_enable
        self.chanctrl[i][2:6] = mode.light_mask
        self.chanctrl[i][6:7] = mode.ambient_source
        self.chanctrl[i][7:9] = mode.diffuse_function if mode.attenuation_function != gx.AF_SPEC else gx.DF_NONE
        self.chanctrl[i][9] = mode.attenuation_function != gx.AF_NONE
        self.chanctrl[i][10] = mode.attenuation_function != gx.AF_SPEC
        self.chanctrl[i][11:15] = mode.light_mask >> 4

    def SetChanMatColor(self,i,color):
        self.matcolor[i][0:8] = color.a
        self.matcolor[i][8:16] = color.b
        self.matcolor[i][16:24] = color.g
        self.matcolor[i][24:32] = color.r

    def SetChanAmbColor(self,i,color):
        self.ambcolor[i][0:8] = color.a
        self.ambcolor[i][8:16] = color.b
        self.ambcolor[i][16:24] = color.g
        self.ambcolor[i][24:32] = color.r

    def SetLight(self,i,light):
        self.light_color[i][0][0:8] = light.color.a
        self.light_color[i][0][8:16] = light.color.b
        self.light_color[i][0][16:24] = light.color.g
        self.light_color[i][0][24:32] = light.color.r
        self.light_attn[i][0] = light.a0
        self.light_attn[i][1] = light.a1
        self.light_attn[i][2] = light.a2
        self.light_attn[i][3] = light.k0
        self.light_attn[i][4] = light.k1
        self.light_attn[i][5] = light.k2
        self.light_pos[i][0] = light.position.x
        self.light_pos[i][1] = light.position.y
        self.light_pos[i][2] = light.position.z
        self.light_dir[i][0] = light.direction.x
        self.light_dir[i][1] = light.direction.y
        self.light_dir[i][2] = light.direction.z

    def SetNumTexGens(self,count):
        self.genmode[0:4] = count
        self.numtexgens[0] = count

    def SetTexCoordGen(self,i,generator):
        self.texcoordgen0[i][2:3] = generator.source in {gx.TG_POS,gx.TG_NRM,gx.TG_BINRM,gx.TG_TANGENT}
        self.texcoordgen0[i][7:12] = convert_texcoord_source(generator.source)
        self.texcoordgen0[i][12:15] = 5

        if generator.function == gx.TG_MTX3x4:
            self.texcoordgen0[i][1:2] = 1
        elif generator.function in gx.TG_BUMP:
            self.texcoordgen0[i][4:7] = 1
            self.texcoordgen0[i][12:15] = generator.source.index
            self.texcoordgen0[i][15:18] = generator.function.index
        elif generator.function == gx.TG_SRTG:
            self.texcoordgen0[i][4:7] = generator.source.index + 2

        self.texcoordgen1[i][8] = False
        self.texcoordgen1[i][0:6] = gx.PTTIDENTITY - gx.PTTMTX0

        index,offset = divmod(6 + 6*i,30)
        self.mtxidx[index][offset:offset + 6] = generator.matrix

    def SetTexCoordScale(self,i,texture):
        self.su_ssize[i][0:16] = texture.width - 1
        self.su_tsize[i][0:16] = texture.height - 1

    def SetTexMatrix(self,i,matrix):
        self.texmtx[i][:] = matrix.create_matrix().flat

    def SetTexture(self,i,texture_index,texture):
        self.tx_setimage0[i][0:10] = texture.width - 1
        self.tx_setimage0[i][10:20] = texture.height - 1
        self.tx_setimage0[i][20:24] = texture.image_format
        self.tx_setimage3[i][0:24] = texture_index
        self.tx_setmode0[i][0:2] = texture.wrap_s
        self.tx_setmode0[i][2:4] = texture.wrap_t
        self.tx_setmode0[i][4] = texture.magnification_filter == gx.LINEAR
        self.tx_setmode0[i][5:8] = convert_minification_filter(texture.minification_filter)
        self.tx_setmode0[i][8] = True
        self.tx_setmode0[i][9:17] = int(32*texture.lod_bias)
        self.tx_setmode0[i][19:21] = gx.ANISO_1
        self.tx_setmode0[i][21] = False
        self.tx_setmode1[i][0:8] = int(16*texture.minimum_lod)
        self.tx_setmode1[i][8:16] = int(16*texture.maximum_lod)

        if texture.image_format in {gx.TF_CI4,gx.TF_CI8,gx.TF_CI14}:
            #XXX BP 0x64 (loadtlut0) is used to specify the address of the
            # palette in main memory, but there is no way to know that address
            # until the model is loaded.
            self.loadtlut0[i][0:24] = 0
            self.loadtlut1[i][0:10] = 0x380 + 16*i
            self.loadtlut1[i][10:20] = 1 if len(texture.palette) == 16 else 16
            self.tx_settlut[i][0:10] = 0x380 + 16*i
            self.tx_settlut[i][10:12] = texture.palette.palette_format

    def SetTextureIndirect(self,i):
        self.ind_imask[i] = True

    def SetNumTevStages(self,count):
        self.genmode[10:14] = count - 1

    def SetTevOrder(self,i,stage):
        index,offset = divmod(12*i,24)
        self.tref[index][offset:offset + 3] = stage.texture
        self.tref[index][offset + 3:offset + 6] = stage.texcoord if stage.texture != gx.TEXMAP_NULL else 0
        self.tref[index][offset + 6] = stage.texture != gx.TEXMAP_NULL
        self.tref[index][offset + 7:offset + 10] = convert_rasterized_color(stage.color)

    def SetTevColorIn(self,i,mode):
        self.tev_color_env[i][0:4] = mode.d
        self.tev_color_env[i][4:8] = mode.c
        self.tev_color_env[i][8:12] = mode.b
        self.tev_color_env[i][12:16] = mode.a

    def SetTevAlphaIn(self,i,mode):
        self.tev_alpha_env[i][4:7] = mode.d
        self.tev_alpha_env[i][7:10] = mode.c
        self.tev_alpha_env[i][10:13] = mode.b
        self.tev_alpha_env[i][13:16] = mode.a

    def SetTevColorOp(self,i,mode):
        self.tev_color_env[i][18:19] = mode.function
        self.tev_color_env[i][19] = mode.clamp
        self.tev_color_env[i][22:24] = mode.output
        
        if mode.function in {gx.TEV_ADD,gx.TEV_SUB}:
            self.tev_color_env[i][16:18] = mode.bias
            self.tev_color_env[i][20:22] = mode.scale
        else:
            self.tev_color_env[i][16:18] = 3
            self.tev_color_env[i][20:22] = mode.function >> 1

    def SetTevAlphaOp(self,i,mode):
        self.tev_alpha_env[i][18:19] = mode.function
        self.tev_alpha_env[i][19] = mode.clamp
        self.tev_alpha_env[i][22:24] = mode.output
        
        if mode.function in {gx.TEV_ADD,gx.TEV_SUB}:
            self.tev_alpha_env[i][16:18] = mode.bias
            self.tev_alpha_env[i][20:22] = mode.scale
        else:
            self.tev_alpha_env[i][16:18] = 3
            self.tev_alpha_env[i][20:22] = mode.function >> 1

    def SetTevKColorSel(self,i,constant_color):
        index,offset = divmod(4 + 10*i,20)
        self.tev_ksel[index][offset:offset + 5] = constant_color

    def SetTevKAlphaSel(self,i,constant_alpha):
        index,offset = divmod(9 + 10*i,20)
        self.tev_ksel[index][offset:offset + 5] = constant_alpha

    def SetTevSwapMode(self,i,stage):
        self.tev_alpha_env[i][0:2] = stage.color_swap_table
        self.tev_alpha_env[i][2:4] = stage.texture_swap_table

    def SetTevIndirect(self,i,stage):
        self.ind_cmd[i][0:2] = stage.indirect_stage
        self.ind_cmd[i][2:4] = stage.indirect_format
        self.ind_cmd[i][4:7] = stage.indirect_bias_components
        self.ind_cmd[i][7:9] = stage.bump_alpha
        self.ind_cmd[i][9:13] = stage.indirect_matrix
        self.ind_cmd[i][13:16] = stage.wrap_s
        self.ind_cmd[i][16:19] = stage.wrap_t
        self.ind_cmd[i][19] = stage.use_original_lod
        self.ind_cmd[i][20] = stage.add_previous_texcoord

    def SetTevColor(self,i,color):
        self.tev_color_ra[i][0:11] = color.r
        self.tev_color_ra[i][12:23] = color.a
        self.tev_color_bg[i][0:11] = color.b
        self.tev_color_bg[i][12:23] = color.g

    def SetTevKColor(self,i,color):
        self.kcolor_ra[i][0:11] = color.r
        self.kcolor_ra[i][12:23] = color.a
        self.kcolor_bg[i][0:11] = color.b
        self.kcolor_bg[i][12:23] = color.g

    def SetTevSwapModeTable(self,i,table):
        self.tev_ksel[2*i][0:2] = table.r
        self.tev_ksel[2*i][2:4] = table.g
        self.tev_ksel[2*i + 1][0:2] = table.b
        self.tev_ksel[2*i + 1][2:4] = table.a

    def SetNumIndStages(self,count):
        self.genmode[16:19] = count

    def SetIndTexCoordScale(self,i,stage):
        index,offset = divmod(8*i,24)
        self.ras1_ss[index][offset:offset + 4] = stage.scale_s
        self.ras1_ss[index][offset + 4:offset + 8] = stage.scale_t

    def SetIndTexOrder(self,i,stage):
        self.iref[6*i:6*i + 3] = stage.texture
        self.iref[6*i + 3:6*i + 6] = stage.texcoord

    def SetIndTexMatrix(self,i,matrix):
        s = matrix.scale_exponent + 17
        self.ind_mtxa[i][0:11] = int(1024*matrix.significand_matrix[0][0])
        self.ind_mtxa[i][11:22] = int(1024*matrix.significand_matrix[1][0])
        self.ind_mtxa[i][22:24] = s
        self.ind_mtxb[i][0:11] = int(1024*matrix.significand_matrix[0][1])
        self.ind_mtxb[i][11:22] = int(1024*matrix.significand_matrix[1][1])
        self.ind_mtxb[i][22:24] = s >> 2
        self.ind_mtxc[i][0:11] = int(1024*matrix.significand_matrix[0][2])
        self.ind_mtxc[i][11:22] = int(1024*matrix.significand_matrix[1][2])
        self.ind_mtxc[i][22:24] = s >> 4

    def SetCullMode(self,mode):
        self.genmode[14:16] = convert_cull_mode(mode)

    def SetFog(self,fog):
        projection = (fog.function >> 3) & 1

        if projection:
            if fog.z_far == fog.z_near or fog.z_end == fog.z_start:
                A = 0
                C = 0
            else:
                A = (fog.z_far - fog.z_near)/(fog.z_end - fog.z_start)
                C = (fog.z_start - fog.z_near)/(fog.z_end - fog.z_start)
            b_shift = 0
            b_magnitude = 0

        else:
            if fog.z_far == fog.z_near or fog.z_end == fog.z_start:
                A = 0
                B = 0.5
                C = 0
            else:
                A = fog.z_far*fog.z_near/((fog.z_far - fog.z_near)*(fog.z_end - fog.z_start))
                B = fog.z_far/(fog.z_far - fog.z_near)
                C = fog.z_start/(fog.z_end - fog.z_start)

            if B > 1:
                b_shift = 1 + int(ceil(log(B,2)))
            elif 0 < B < 0.5:
                b_shift = 0
            else:
                b_shift = 1

            A /= 2**b_shift
            b_magnitude = int(2*(B/2**b_shift)*8388638)


        a_mantissa,a_exponent = frexp(A)
        self.fog_param0[0:11] = int(abs(a_mantissa)*2**12) & 0x7FF
        self.fog_param0[11:19] = a_exponent + 126 if A != 0 else 0
        self.fog_param0[19] = a_mantissa < 0

        self.fog_param1[0:24] = b_magnitude
        self.fog_param2[0:5] = b_shift

        c_mantissa,c_exponent = frexp(C)
        self.fog_param3[0:11] = int(abs(c_mantissa)*2**12) & 0x7FF
        self.fog_param3[11:19] = c_exponent + 126 if C != 0 else 0
        self.fog_param3[19] = c_mantissa < 0
        self.fog_param3[20:21] = projection
        self.fog_param3[21:24] = fog.function

        self.fog_color[0:8] = fog.color.b
        self.fog_color[8:16] = fog.color.g
        self.fog_color[16:24] = fog.color.r

    def SetFogRangeAdj(self,fog):
        self.fog_range[0:10] = fog.range_adjustment_center + 342
        self.fog_range[10] = fog.range_adjustment_enable

        if fog.range_adjustment_enable:
            for i in range(10):
                index,offset = divmod(12*i,24)
                self.fog_table[index][offset:offset + 12] = fog.range_adjustment_table[i]

    def SetAlphaCompare(self,mode):
        self.alphacompare[0:8] = mode.reference0
        self.alphacompare[8:16] = mode.reference1
        self.alphacompare[16:19] = mode.function0
        self.alphacompare[19:22] = mode.function1
        self.alphacompare[22:24] = mode.operation

    def SetBlendMode(self,mode):
        self.blendmode[0] = mode.function in {gx.BM_BLEND,gx.BM_SUBTRACT}
        self.blendmode[1] = mode.function == gx.BM_LOGIC
        self.blendmode[5:8] = mode.destination_factor
        self.blendmode[11] = mode.function == gx.BM_SUBTRACT
        self.blendmode[8:11] = mode.source_factor
        self.blendmode[12:16] = mode.logical_operation

    def SetZCompLoc(self,depth_test_early):
        self.zcompare[6] = depth_test_early

    def SetZMode(self,mode):
        self.zmode[0] = mode.enable
        self.zmode[1:4] = mode.function
        self.zmode[4] = mode.update_enable

    def SetDither(self,dither):
        self.blendmode[2] = dither


def pack_texture_subpacket(stream,packet,material,textures):
    for i in range(8):
        if not packet.use_texture[i]: continue

        BPCommand.pack(stream,packet.tx_setimage3[i])
        BPCommand.pack(stream,packet.tx_setimage0[i])
        BPCommand.pack(stream,packet.tx_setmode0[i])
        BPCommand.pack(stream,packet.tx_setmode1[i])

        if textures[material.texture_indices[i]].image_format in {gx.TF_CI4,gx.TF_CI8,gx.TF_CI14}:
            BPCommand.pack(stream,BPMask(0xFFFF00))
            BPCommand.pack(stream,BPCommand(0x0F,0))
            BPCommand.pack(stream,packet.loadtlut0[i])
            BPCommand.pack(stream,packet.loadtlut1[i])
            BPCommand.pack(stream,BPMask(0xFFFF00))
            BPCommand.pack(stream,BPCommand(0x0F,0))
            BPCommand.pack(stream,packet.tx_settlut[i])

    for i in range((material.tev_stage_count + 1)//2):
        BPCommand.pack(stream,packet.tref[i])

        for j in range(2):
            stage = material.tev_stages[2*i + j]
            use_texture = stage.texture != gx.TEXMAP_NULL
            texcoord = stage.texcoord if use_texture else gx.TEXCOORD7
            BPCommand.pack(stream,BPMask(0x03FFFF))
            BPCommand.pack(stream,packet.su_ssize[texcoord.index])
            BPCommand.pack(stream,packet.su_tsize[texcoord.index])


def pack_tev_subpacket(stream,packet,material):
    # Notice that GX_TEVPREV is not set
    for i in gx.TEVREG:
        BPCommand.pack(stream,packet.tev_color_ra[i])
        BPCommand.pack(stream,packet.tev_color_bg[i])
        BPCommand.pack(stream,packet.tev_color_bg[i])
        BPCommand.pack(stream,packet.tev_color_bg[i])

    for i in range(4):
        BPCommand.pack(stream,packet.kcolor_ra[i])
        BPCommand.pack(stream,packet.kcolor_bg[i])

    for i in range(material.tev_stage_count):
        BPCommand.pack(stream,packet.tev_color_env[i])
        BPCommand.pack(stream,packet.tev_alpha_env[i])
        BPCommand.pack(stream,packet.ind_cmd[i])

    for i in range(8):
        BPCommand.pack(stream,packet.tev_ksel[i])

    # This is what Nintendo does, though I would say that this is wrong. The
    # number of enabled indirect texture stages does not in general have anything
    # to do with which indirect texture matrices that are used.
    for i in range(material.indirect_stage_count):
        BPCommand.pack(stream,packet.ind_mtxa[i])
        BPCommand.pack(stream,packet.ind_mtxb[i])
        BPCommand.pack(stream,packet.ind_mtxc[i])

    for i in range((material.indirect_stage_count + 1)//2):
        BPCommand.pack(stream,packet.ras1_ss[i])

    for i,stage in enumerate(material.enabled_indirect_stages):
        BPCommand.pack(stream,BPMask(0x03FFFF))
        BPCommand.pack(stream,packet.su_ssize[stage.texcoord.index])
        BPCommand.pack(stream,packet.su_tsize[stage.texcoord.index])

    # These commands for the disabled indirect stages might seem a bit odd, but
    # notice that 0x30 + 2*(-1) = 0x2E and 0x31 + 2*(-1) = 0x2F
    for i in range(4 - material.indirect_stage_count):
        BPCommand.pack(stream,BPMask(0x03FFFF))
        BPCommand.pack(stream,BPCommand(0x2E))
        BPCommand.pack(stream,BPCommand(0x2F))

    BPCommand.pack(stream,packet.iref)
    BPCommand.pack(stream,packet.ind_imask)


def pack_fog_subpacket(stream,packet,material):
    BPCommand.pack(stream,packet.fog_param0)
    BPCommand.pack(stream,packet.fog_param1)
    BPCommand.pack(stream,packet.fog_param2)
    BPCommand.pack(stream,packet.fog_param3)
    BPCommand.pack(stream,packet.fog_color)

    if material.fog.range_adjustment_enable:
        for i in range(5):
            BPCommand.pack(stream,packet.fog_table[i])

    BPCommand.pack(stream,packet.fog_range)

    BPCommand.pack(stream,packet.alphacompare)
    # In Wind Waker this mask is 0x001FE7
    BPCommand.pack(stream,BPMask(0x00FFE7))
    BPCommand.pack(stream,packet.blendmode)
    BPCommand.pack(stream,packet.zmode)
    BPCommand.pack(stream,BPMask(0x000040))
    BPCommand.pack(stream,packet.zcompare)
    BPCommand.pack(stream,BPMask(0x07FC3F))
    BPCommand.pack(stream,packet.genmode)


def pack_texcoord_generator_subpacket(stream,packet,material):
    for i in range(10):
        if not packet.use_texture_matrix[i]: continue
        XFCommand.pack(stream,packet.texmtx[i])

    XFCommand.pack(stream,packet.texcoordgen0[0:material.texcoord_generator_count])
    XFCommand.pack(stream,packet.texcoordgen1[0:material.texcoord_generator_count])


def pack_channel_color_subpacket(stream,packet):
    XFCommand.pack(stream,packet.matcolor)
    XFCommand.pack(stream,packet.ambcolor)


def pack_channel_subpacket(stream,packet,material):
    XFCommand.pack(stream,packet.chanctrl)

    for i in range(8):
        if material.lights[i] is None: continue
        XFCommand.pack(stream,packet.light_pos[i])
        XFCommand.pack(stream,packet.light_attn[i])
        XFCommand.pack(stream,packet.light_color[i])
        XFCommand.pack(stream,packet.light_dir[i])

    XFCommand.pack(stream,packet.numchans)
    XFCommand.pack(stream,packet.numtexgens)


def pack_packet(stream,packet,material,textures):
    base = stream.tell()

    packet.texture_offset = stream.tell() - base
    pack_texture_subpacket(stream,packet,material,textures)

    packet.tev_offset = stream.tell() - base
    pack_tev_subpacket(stream,packet,material)

    packet.fog_offset = stream.tell() - base
    pack_fog_subpacket(stream,packet,material)

    packet.texcoord_generator_offset = stream.tell() - base
    pack_texcoord_generator_subpacket(stream,packet,material)

    packet.channel_color_offset = stream.tell() - base
    pack_channel_color_subpacket(stream,packet)

    packet.channel_offset = stream.tell() - base
    pack_channel_subpacket(stream,packet,material)

    align(stream,0x20,b'\x00')


def pack(stream,materials,textures):
    base = stream.tell()
    header = Header()
    header.packet_count = len(materials)
    stream.write(b'\x00'*Header.sizeof())

    packets = [Packet(material,textures) for material in materials]
    packet_locations = []

    align(stream,0x20)
    header.packet_offset = stream.tell() - base
    stream.write(b'\x00'*header.packet_count*PacketLocation.sizeof())
    align(stream,0x20)

    for i,(packet,material) in enumerate(zip(packets,materials)):
        packet_base = base + header.packet_offset + i*PacketLocation.sizeof()
        packet_location = PacketLocation()
        packet_location.offset = stream.tell() - packet_base
        pack_packet(stream,packet,material,textures)
        packet_location.size = stream.tell() - packet_base - packet_location.offset
        packet_locations.append(packet_location)

    header.subpacket_location_offset = stream.tell() - base
    for packet in packets:
        SubpacketLocation.pack(stream,packet)

    header.matrix_index_offset = stream.tell() - base
    for packet in packets:
        uint32.pack(stream,packet.mtxidx[0])
        uint32.pack(stream,packet.mtxidx[1])

    header.unknown0_offset = stream.tell() - base
    for material in materials:
        uint8.pack(stream,material.unknown0)

    align(stream,4)
    header.index_offset = stream.tell() - base
    for i in range(header.packet_count):
        uint16.pack(stream,i)

    align(stream,4)
    header.name_offset = stream.tell() - base
    j3d.string_table.pack(stream,(material.name for material in materials))
    
    align(stream,0x20)
    header.section_size = stream.tell() - base

    stream.seek(base)
    Header.pack(stream,header)

    stream.seek(base + header.packet_offset)
    for packet_location in packet_locations:
        PacketLocation.pack(stream,packet_location)

    stream.seek(base + header.section_size)

