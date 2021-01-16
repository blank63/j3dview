from io import StringIO
import gx
from OpenGL.GL.ARB.shader_image_load_store import *


class Scalar:

    def __init__(self,value,component_count=4):
        self.value = value
        self.component_count = component_count

    def __getitem__(self,key):
        return getattr(self,key)

    def __getattr__(self,attribute):
        return Scalar(self.value,len(attribute))

    def __eq__(self,other):
        if not isinstance(other,Scalar):
            return self.value == other
        return self.value == other.value and self.component_count == other.component_count

    def __str__(self):
        if self.component_count == 1:
            return str(self.value)
        return 'vec{}({})'.format(self.component_count,self.value)

    def swap(self,table): #<-?
        return self


class Vector: #<-?

    component_map = {'r':0,'g':1,'b':2,'a':3} #<-?

    def __init__(self,name,components='rgba'):
        self.name = name
        self.components = components

    def __getitem__(self,key):
        return getattr(self,key)

    def __getattr__(self,attribute):
        return Vector(self.name,''.join(self.components[self.component_map[component]] for component in attribute))

    def __eq__(self,other):
        if not isinstance(other,Vector):
            return False
        return self.name == other.name and self.components == other.components

    def __str__(self):
        if self.components == 'rgba':
            return self.name
        return self.name + '.' + self.components

    def swap(self,table): #<-?
        r = self.components[table.r]
        g = self.components[table.g]
        b = self.components[table.b]
        a = self.components[table.a]
        return Vector(self.name,r + g + b + a)

#------------------------------------------------------------------------------

def convert_indirect_texcoord_scale(scale):
    if scale == gx.ITS_1:
        return 1
    if scale == gx.ITS_2:
        return 1/2
    if scale == gx.ITS_4:
        return 1/4
    if scale == gx.ITS_8:
        return 1/8
    if scale == gx.ITS_16:
        return 1/16
    if scale == gx.ITS_32:
        return 1/32
    if scale == gx.ITS_64:
        return 1/64
    if scale == gx.ITS_128:
        return 1/128
    if scale == gx.ITS_256:
        return 1/256

    raise ValueError('invalid indirect texture coordinate scale')


def write_indirect_stage(stream,index,stage):
    texcoord_index = gx.TEXCOORD.index(stage.texcoord)
    texture_index = gx.TEXMAP.index(stage.texture)
    stream.write('vec3 indtex{} = texture(texmap{},'.format(index,texture_index))
    if stage.scale_s != gx.ITS_1 or stage.scale_t != gx.ITS_1:
        scale_s = convert_indirect_texcoord_scale(stage.scale_s)
        scale_t = convert_indirect_texcoord_scale(stage.scale_t)
        stream.write('vec2({},{})*'.format(scale_s,scale_t))
    stream.write('uv{}).abg;\n'.format(texcoord_index))

#------------------------------------------------------------------------------

def convert_ras(color): #<-?
    if color in (gx.COLOR0,gx.ALPHA0,gx.COLOR0A0):
        return Vector('channel0')
    if color in (gx.COLOR1,gx.ALPHA1,gx.COLOR1A1):
        return Vector('channel1')
    if color in (gx.ALPHA_BUMP,gx.ALPHA_BUMPN):
        return Scalar('alphabump')
    if color == gx.COLOR_ZERO:
        return Scalar(0.0)
    if color == gx.COLOR_NULL:
        return Scalar(0.0) #TODO

    raise ValueError('invalid TEV rasterized color')


def convert_kcolorsel(kcolorsel):
    if kcolorsel == gx.TEV_KCSEL_1:
        return Scalar(1.0,3)
    if kcolorsel == gx.TEV_KCSEL_7_8:
        return Scalar(0.875,3)
    if kcolorsel == gx.TEV_KCSEL_3_4:
        return Scalar(0.75,3)
    if kcolorsel == gx.TEV_KCSEL_5_8:
        return Scalar(0.625,3)
    if kcolorsel == gx.TEV_KCSEL_1_2:
        return Scalar(0.5,3)
    if kcolorsel == gx.TEV_KCSEL_3_8:
        return Scalar(0.375,3)
    if kcolorsel == gx.TEV_KCSEL_1_4:
        return Scalar(0.25,3)
    if kcolorsel == gx.TEV_KCSEL_1_8:
        return Scalar(0.125,3)
    if kcolorsel == gx.TEV_KCSEL_K0:
        return Vector('kcolor0').rgb
    if kcolorsel == gx.TEV_KCSEL_K1:
        return Vector('kcolor1').rgb
    if kcolorsel == gx.TEV_KCSEL_K2:
        return Vector('kcolor2').rgb
    if kcolorsel == gx.TEV_KCSEL_K3:
        return Vector('kcolor3').rgb
    if kcolorsel == gx.TEV_KCSEL_K0_R:
        return Vector('kcolor0').rrr
    if kcolorsel == gx.TEV_KCSEL_K1_R:
        return Vector('kcolor1').rrr
    if kcolorsel == gx.TEV_KCSEL_K2_R:
        return Vector('kcolor2').rrr
    if kcolorsel == gx.TEV_KCSEL_K3_R:
        return Vector('kcolor3').rrr
    if kcolorsel == gx.TEV_KCSEL_K0_G:
        return Vector('kcolor0').ggg
    if kcolorsel == gx.TEV_KCSEL_K1_G:
        return Vector('kcolor1').ggg
    if kcolorsel == gx.TEV_KCSEL_K2_G:
        return Vector('kcolor2').ggg
    if kcolorsel == gx.TEV_KCSEL_K3_G:
        return Vector('kcolor3').ggg
    if kcolorsel == gx.TEV_KCSEL_K0_B:
        return Vector('kcolor0').bbb
    if kcolorsel == gx.TEV_KCSEL_K1_B:
        return Vector('kcolor1').bbb
    if kcolorsel == gx.TEV_KCSEL_K2_B:
        return Vector('kcolor2').bbb
    if kcolorsel == gx.TEV_KCSEL_K3_B:
        return Vector('kcolor3').bbb
    if kcolorsel == gx.TEV_KCSEL_K0_A:
        return Vector('kcolor0').aaa
    if kcolorsel == gx.TEV_KCSEL_K1_A:
        return Vector('kcolor1').aaa
    if kcolorsel == gx.TEV_KCSEL_K2_A:
        return Vector('kcolor2').aaa
    if kcolorsel == gx.TEV_KCSEL_K3_A:
        return Vector('kcolor3').aaa

    raise ValueError('invalid TEV constant color selection')


def convert_kalphasel(kalphasel):
    if kalphasel == gx.TEV_KASEL_1:
        return Scalar(1.0,1)
    if kalphasel == gx.TEV_KASEL_7_8:
        return Scalar(0.875,1)
    if kalphasel == gx.TEV_KASEL_3_4:
        return Scalar(0.75,1)
    if kalphasel == gx.TEV_KASEL_5_8:
        return Scalar(0.625,1)
    if kalphasel == gx.TEV_KASEL_1_2:
        return Scalar(0.5,1)
    if kalphasel == gx.TEV_KASEL_3_8:
        return Scalar(0.375,1)
    if kalphasel == gx.TEV_KASEL_1_4:
        return Scalar(0.25,1)
    if kalphasel == gx.TEV_KASEL_1_8:
        return Scalar(0.125,1)
    if kalphasel == gx.TEV_KASEL_K0_R:
        return Vector('kcolor0').r
    if kalphasel == gx.TEV_KASEL_K1_R:
        return Vector('kcolor1').r
    if kalphasel == gx.TEV_KASEL_K2_R:
        return Vector('kcolor2').r
    if kalphasel == gx.TEV_KASEL_K3_R:
        return Vector('kcolor3').r
    if kalphasel == gx.TEV_KASEL_K0_G:
        return Vector('kcolor0').g
    if kalphasel == gx.TEV_KASEL_K1_G:
        return Vector('kcolor1').g
    if kalphasel == gx.TEV_KASEL_K2_G:
        return Vector('kcolor2').g
    if kalphasel == gx.TEV_KASEL_K3_G:
        return Vector('kcolor3').g
    if kalphasel == gx.TEV_KASEL_K0_B:
        return Vector('kcolor0').b
    if kalphasel == gx.TEV_KASEL_K1_B:
        return Vector('kcolor1').b
    if kalphasel == gx.TEV_KASEL_K2_B:
        return Vector('kcolor2').b
    if kalphasel == gx.TEV_KASEL_K3_B:
        return Vector('kcolor3').b
    if kalphasel == gx.TEV_KASEL_K0_A:
        return Vector('kcolor0').a
    if kalphasel == gx.TEV_KASEL_K1_A:
        return Vector('kcolor1').a
    if kalphasel == gx.TEV_KASEL_K2_A:
        return Vector('kcolor2').a
    if kalphasel == gx.TEV_KASEL_K3_A:
        return Vector('kcolor3').a

    raise ValueError('invalid TEV constant alpha selection')


def convert_color_input(color_input,color,texture,konst):
    if color_input == gx.CC_CPREV:
        return Vector('tevprev')
    if color_input == gx.CC_APREV:
        return Vector('tevprev').aaaa
    if color_input == gx.CC_C0:
        return Vector('tevreg0')
    if color_input == gx.CC_A0:
        return Vector('tevreg0').aaaa
    if color_input == gx.CC_C1:
        return Vector('tevreg1')
    if color_input == gx.CC_A1:
        return Vector('tevreg1').aaaa
    if color_input == gx.CC_C2:
        return Vector('tevreg2')
    if color_input == gx.CC_A2:
        return Vector('tevreg2').aaaa
    if color_input == gx.CC_TEXC:
        return texture
    if color_input == gx.CC_TEXA:
        return texture.aaaa
    if color_input == gx.CC_RASC:
        return color
    if color_input == gx.CC_RASA:
        return texture.aaaa
    if color_input == gx.CC_ONE:
        return Scalar(1.0)
    if color_input == gx.CC_HALF:
        return Scalar(0.5)
    if color_input == gx.CC_KONST:
        return konst
    if color_input == gx.CC_ZERO:
        return Scalar(0.0)

    raise ValueError('inavlid TEV color combiner input')


def convert_color_input_overflow(color_input,color,texture,konst):
    if color_input == gx.CC_CPREV:
        return Vector('(fract(tevprev*(255.0/256.0))*(256.0/255.0))')
    if color_input == gx.CC_APREV:
        return Scalar('(fract(tevprev.a*(255.0/256.0))*(256.0/255.0))')
    if color_input == gx.CC_C0:
        return Vector('(fract(tevreg0*(255.0/256.0))*(256.0/255.0))')
    if color_input == gx.CC_A0:
        return Scalar('(fract(tevreg0.a*(255.0/256.0))*(256.0/255.0))')
    if color_input == gx.CC_C1:
        return Vector('(fract(tevreg1*(255.0/256.0))*(256.0/255.0))')
    if color_input == gx.CC_A1:
        return Scalar('(fract(tevreg1.a*(255.0/256.0))*(256.0/255.0))')
    if color_input == gx.CC_C2:
        return Vector('(fract(tevreg2*(255.0/256.0))*(256.0/255.0))')
    if color_input == gx.CC_A2:
        return Scalar('(fract(tevreg2.a*(255.0/256.0))*(256.0/255.0))')
    if color_input == gx.CC_TEXC:
        return texture
    if color_input == gx.CC_TEXA:
        return texture.aaaa
    if color_input == gx.CC_RASC:
        return color
    if color_input == gx.CC_RASA:
        return texture.aaaa
    if color_input == gx.CC_ONE:
        return Scalar(1.0)
    if color_input == gx.CC_HALF:
        return Scalar(0.5)
    if color_input == gx.CC_KONST:
        return konst
    if color_input == gx.CC_ZERO:
        return Scalar(0.0)

    raise ValueError('inavlid TEV color combiner input')


def convert_alpha_input(alpha_input,color,texture,konst):
    if alpha_input == gx.CA_APREV:
        return Vector('tevprev')
    if alpha_input == gx.CA_A0:
        return Vector('tevreg0')
    if alpha_input == gx.CA_A1:
        return Vector('tevreg1')
    if alpha_input == gx.CA_A2:
        return Vector('tevreg2')
    if alpha_input == gx.CA_TEXA:
        return texture
    if alpha_input == gx.CA_RASA:
        return color
    if alpha_input == gx.CA_KONST:
        return konst
    if alpha_input == gx.CA_ZERO:
        return Scalar(0.0)

    raise ValueError('invalide TEV alpha combiner input')


def convert_alpha_input_overflow(alpha_input,color,texture,konst):
    if alpha_input == gx.CA_APREV:
        return Vector('(fract(tevprev*(255.0/256.0))*(256.0/255.0))')
    if alpha_input == gx.CA_A0:
        return Vector('(fract(tevreg0*(255.0/256.0))*(256.0/255.0))')
    if alpha_input == gx.CA_A1:
        return Vector('(fract(tevreg1*(255.0/256.0))*(256.0/255.0))')
    if alpha_input == gx.CA_A2:
        return Vector('(fract(tevreg2*(255.0/256.0))*(256.0/255.0))')
    if alpha_input == gx.CA_TEXA:
        return texture
    if alpha_input == gx.CA_RASA:
        return color
    if alpha_input == gx.CA_KONST:
        return konst
    if alpha_input == gx.CA_ZERO:
        return Scalar(0.0)

    raise ValueError('invalide TEV alpha combiner input')


def convert_output(output):
    if output == gx.TEVPREV:
        return Vector('tevprev')
    if output == gx.TEVREG0:
        return Vector('tevreg0')
    if output == gx.TEVREG1:
        return Vector('tevreg1')
    if output == gx.TEVREG2:
        return Vector('tevreg2')

    raise ValueError('invalid TEV combiner output')


def convert_operator(operator): #<-?
    if operator == gx.TEV_ADD:
        return '+'
    if operator == gx.TEV_SUB:
        return '-'

    raise ValueError('invalid TEV operator')


def convert_tevscale(scale):
    if scale == gx.CS_SCALE_1:
        return '1.0'
    if scale == gx.CS_SCALE_2:
        return '2.0'
    if scale == gx.CS_SCALE_4:
        return '4.0'
    if scale == gx.CS_DIVIDE_2:
        return '0.5'

    raise ValueError('invalid TEV scale')


def pack_combiner(stream,mode,a,b,c,d,swizzle):
    stream.write('{} = '.format(convert_output(mode.output)[swizzle]))

    if mode.clamp:
        stream.write('clamp(')

    if mode.function in (gx.TEV_ADD,gx.TEV_SUB):
        if mode.scale != gx.CS_SCALE_1:
            stream.write('{}*('.format(convert_tevscale(mode.scale)))

        if not (d[swizzle] == 0 and mode.function == gx.TEV_ADD): #<-?
            stream.write('{} {} '.format(d[swizzle],convert_operator(mode.function)))

        if a[swizzle] == b[swizzle] or c[swizzle] == 0:
            stream.write(str(a[swizzle]))
        elif c[swizzle] == 1:
            stream.write(str(b[swizzle]))
        elif a[swizzle] == 0:
            stream.write('{}*{}'.format(c[swizzle],b[swizzle]))
        elif b[swizzle] == 0:
            stream.write('(1.0 - {})*{}'.format(c[swizzle],a[swizzle]))
        else:
            stream.write('mix({},{},{})'.format(a[swizzle],b[swizzle],c[swizzle]))

        if mode.bias == gx.TB_ZERO: #<-?
            pass
        elif mode.bias == gx.TB_ADDHALF:
            stream.write(' + 0.5')
        elif mode.bias == gx.TB_SUBHALF:
            stream.write(' - 0.5')
        else:
            raise ValueError('invalid TEV bias')

        if mode.scale != gx.CS_SCALE_1:
            stream.write(')')

    elif mode.function == gx.TEV_COMP_R8_GT:
        if swizzle == 'rgb':
            stream.write('{} + (({} >= {} + (0.25/255.0)) ? {} : vec3(0.0))'.format(d[swizzle],a.r,b.r,c[swizzle]))
        else:
            stream.write('{} + (({} >= {} + (0.25/255.0)) ? {} : 0.0)'.format(d[swizzle],a.r,b.r,c[swizzle]))
    elif mode.function == gx.TEV_COMP_R8_EQ:
        if swizzle == 'rgb':
            stream.write('{} + ((abs({} - {}) < (0.5/255.0) ? {} : vec3(0.0))'.format(d[swizzle],a.r,b.r,c[swizzle]))
        else:
            stream.write('{} + ((abs({} - {}) < (0.5/255.0) ? {} : 0.0)'.format(d[swizzle],a.r,b.r,c[swizzle]))
    elif mode.function == gx.TEV_COMP_GR16_GT:
        if swizzle == 'rgb':
            stream.write('{} + ((dot({},vec2(1.0,255.0)) >= (dot({},vec2(1.0,255.0)) + (0.25/255.0))) ? {} : vec3(0.0))'.format(d[swizzle],a.rg,b.rg,c[swizzle]))
        else:
            stream.write('{} + ((dot({},vec2(1.0,255.0)) >= (dot({},vec2(1.0,255.0)) + (0.25/255.0))) ? {} : 0.0)'.format(d[swizzle],a.rg,b.rg,c[swizzle]))
    elif mode.function == gx.TEV_COMP_GR16_EQ:
        if swizzle == 'rgb':
            stream.write('{} + (abs(dot({},vec2(1.0,255.0)) - dot({},vec2(1.0,255.0))) < (0.5/255.0) ? {} : vec3(0.0))'.format(d[swizzle],a.rg,b.rg,c[swizzle]))
        else:
            stream.write('{} + (abs(dot({},vec2(1.0,255.0)) - dot({},vec2(1.0,255.0))) < (0.5/255.0) ? {} : 0.0)'.format(d[swizzle],a.rg,b.rg,c[swizzle]))
    elif mode.function == gx.TEV_COMP_BGR24_GT:
        if swizzle == 'rgb':
            stream.write('{} + ((dot({},vec3(1.0,255.0,255.0*255.0)) >= (dot({},vec3(1.0,255.0,255.0*255.0)) + (0.25/255.0))) ? {} : vec3(0.0))'.format(d[swizzle],a.rgb,b.rgb,c[swizzle]))
        else:
            stream.write('{} + ((dot({},vec3(1.0,255.0,255.0*255.0)) >= (dot({},vec3(1.0,255.0,255.0*255.0)) + (0.25/255.0))) ? {} : 0.0)'.format(d[swizzle],a.rgb,b.rgb,c[swizzle]))
    elif mode.function == gx.TEV_COMP_BGR24_EQ:
        if swizzle == 'rgb':
            stream.write('{} + (abs(dot({},vec3(1.0,255.0,255.0*255.0)) - dot({},vec3(1.0,255.0,255.0*255.0))) < (0.5/255.0) ? {} : vec3(0.0))'.format(d[swizzle],a.rgb,b.rgb,c[swizzle]))
        else:
            stream.write('{} + (abs(dot({},vec3(1.0,255.0,255.0*255.0)) - dot({},vec3(1.0,255.0,255.0*255.0))) < (0.5/255.0) ? {} : 0.0)'.format(d[swizzle],a.rgb,b.rgb,c[swizzle]))
    elif mode.function == gx.TEV_COMP_RGB8_GT:
        if swizzle == 'rgb':
            stream.write('{} + (max(sign({} - {} - (0.25/255.0)),0.0)*{})'.format(d[swizzle],a.rgb,b.rgb,c[swizzle]))
        else:
            stream.write('{} + (({} >= ({} + (0.25/255.0))) ? {} : 0.0)'.format(d[swizzle],a.a,b.a,c[swizzle]))
    elif mode.function == gx.TEV_COMP_RGB8_EQ:
        if swizzle == 'rgb':
            stream.write('{} + ((1.0 - max(sign(abs({} - {}) - (0.5/255.0)),0.0))*{})'.format(d[swizzle],a.rgb,b.rgb,c[swizzle]))
        else:
            stream.write('{} + (abs({} - {}) < (0.5/255.0) ? {} : 0.0)'.format(d[swizzle],a.a,b.a,c[swizzle]))
    else:
        raise ValueError('invalide TEV combiner function')

    if mode.clamp:
        stream.write(',0.0,1.0)')

    stream.write(';\n')


def convert_bump_alpha(selection): #<-?
    if selection == gx.ITBA_S:
        return 's'
    if selection == gx.ITBA_T:
        return 't'
    if selection == gx.ITBA_U:
        return 'p'

    raise ValueError('invalid bump alpha')


def convert_bias_selection(selection):
    if selection == gx.ITB_S:
        return 's'
    if selection == gx.ITB_T:
        return 't'
    if selection == gx.ITB_U:
        return 'p'
    if selection == gx.ITB_ST:
        return 'st'
    if selection == gx.ITB_SU:
        return 'sp'
    if selection == gx.ITB_TU:
        return 'tp'
    if selection == gx.ITB_STU:
        return 'stp'

    raise ValueError('invalid indirect texture bias selection')


def convert_wrap(wrap):
    if wrap == gx.ITW_256:
        return 256.0
    if wrap == gx.ITW_128:
        return 128.0
    if wrap == gx.ITW_64:
        return 64.0
    if wrap == gx.ITW_32:
        return 32.0
    if wrap == gx.ITW_16:
        return 16.0
    if wrap == gx.ITW_0:
        return 0.0

    raise ValueError('invalid indirect texture wrap')


def write_tev_stage(stream,stage,material):
    if stage.indirect_format == gx.ITF_8:
        indirect_scale = 2**8
        alphabump_scale = 2**5
        bias = -128
    elif stage.indirect_format == gx.ITF_5:
        indirect_scale = 2**5
        alphabump_scale = 2**3
        bias = 1
    elif stage.indirect_format == gx.ITF_4:
        indirect_scale = 2**4
        alphabump_scale = 2**4
        bias = 1
    elif stage.indirect_format == gx.ITF_3:
        indirect_scale = 2**3
        alphabump_scale = 2**5
        bias = 1
    else:
        raise ValueError('invalid indirect texture format')

    indirect_stage_index = gx.INDTEXSTAGE.index(stage.indirect_stage)
    if stage.bump_alpha != gx.ITBA_OFF:
        stream.write('alphabump = ')
        if stage.color == gx.ALPHA_BUMPN:
            stream.write('(255.0/248.0)*')
        stream.write('floor({0}*indtex{1}.{2})/{0}'.format(alphabump_scale,indirect_stage_index,convert_bump_alpha(stage.bump_alpha))) #<-?
        stream.write(';\n')

    if stage.texcoord != gx.TEXCOORD_NULL:
        texcoord_index = gx.TEXCOORD.index(stage.texcoord)
    if stage.texture != gx.TEXMAP_NULL:
        texture_index = gx.TEXMAP.index(stage.texture)

    if stage.indirect_matrix == gx.ITM_OFF:
        stream.write('indtevtrans = vec2(0.0);\n')
    else:
        if stage.indirect_format == gx.ITF_8:
            stream.write('indtevcrd = 255.0*indtex{};\n'.format(indirect_stage_index))
        else:
            stream.write('indtevcrd = mod(255.0*indtex{},{});\n'.format(indirect_stage_index,indirect_scale))

        if stage.indirect_bias_components != gx.ITB_NONE:
            stream.write('indtevcrd.{} += {};\n'.format(convert_bias_selection(stage.indirect_bias_components),bias))

        if stage.indirect_matrix in gx.ITM:
            matrix_index = gx.ITM.index(stage.indirect_matrix)
            stream.write('indtevtrans = indmatrix{}*indtevcrd;\n'.format(matrix_index))
        elif stage.indirect_matrix in gx.ITM_S:
            matrix_index = gx.ITM_S.index(stage.indirect_matrix)
            scale = 2**material.indirect_matrices[matrix_index].scale_exponent
            stream.write('indtevtrans = {}*indtevcrd.s*uv{};\n'.format(scale/256,texcoord_index))
        elif stage.indirect_matrix in gx.ITM_T:
            matrix_index = gx.ITM_T.index(stage.indirect_matrix)
            scale = 2**material.indirect_matrices[matrix_index].scale_exponent
            stream.write('indtevtrans = {}*indtevcrd.t*uv{};\n'.format(scale/256,texcoord_index))
        else:
            raise ValueError('invalid indirect texture matrix')

    #TODO: scaling of texcoords to texture size needs some work

    if stage.texture != gx.TEXMAP_NULL:
        stream.write('indtevtrans /= textureSize(texmap{},0);\n'.format(texture_index))

    if stage.texcoord == gx.TEXCOORD_NULL or stage.wrap_s == gx.ITW_0:
        stream.write('wrappedcoord.s = 0.0;\n')
    elif stage.wrap_s == gx.ITW_OFF:
        stream.write('wrappedcoord.s = uv{}.s;\n'.format(texcoord_index))
    else:
        stream.write('wrappedcoord.s = mod(uv{}.s,{});\n'.format(texcoord_index,convert_wrap(stage.wrap_s)))

    if stage.texcoord == gx.TEXCOORD_NULL or stage.wrap_t == gx.ITW_0:
        stream.write('wrappedcoord.t = 0.0;\n')
    elif stage.wrap_t == gx.ITW_OFF:
        stream.write('wrappedcoord.t = uv{}.t;\n'.format(texcoord_index))
    else:
        stream.write('wrappedcoord.t = mod(uv{}.t,{});\n'.format(texcoord_index,convert_wrap(stage.wrap_s)))

    if stage.add_previous_texcoord:
        stream.write('tevcoord += wrappedcoord + indtevtrans;\n')
    else:
        stream.write('tevcoord = wrappedcoord + indtevtrans;\n')

    if stage.texture != gx.TEXMAP_NULL:
        if stage.use_original_lod:
            lod = 'textureQueryLod(texmap{},uv{})'.format(texture_index,texcoord_index)
            stream.write('textemp = textureLod(texmap{},tevcoord,{});\n'.format(texture_index,lod))
        else:
            stream.write('textemp = texture(texmap{},tevcoord);\n'.format(texture_index))

    texture_swap_table_index = gx.TEV_SWAP.index(stage.texture_swap_table)
    color_swap_table_index = gx.TEV_SWAP.index(stage.color_swap_table)
    texture = Vector('textemp').swap(material.swap_tables[texture_swap_table_index])
    color = convert_ras(stage.color).swap(material.swap_tables[color_swap_table_index])
    konst = convert_kcolorsel(stage.constant_color)
    konst.a = convert_kalphasel(stage.constant_alpha)

    ca = convert_color_input_overflow(stage.color_mode.a,color,texture,konst)
    cb = convert_color_input_overflow(stage.color_mode.b,color,texture,konst)
    cc = convert_color_input_overflow(stage.color_mode.c,color,texture,konst)
    cd = convert_color_input(stage.color_mode.d,color,texture,konst)

    aa = convert_alpha_input_overflow(stage.alpha_mode.a,color,texture,konst)
    ab = convert_alpha_input_overflow(stage.alpha_mode.b,color,texture,konst)
    ac = convert_alpha_input_overflow(stage.alpha_mode.c,color,texture,konst)
    ad = convert_alpha_input(stage.alpha_mode.d,color,texture,konst)

    pack_combiner(stream,stage.color_mode,ca,cb,cc,cd,'rgb')
    pack_combiner(stream,stage.alpha_mode,aa,ab,ac,ad,'a')

#------------------------------------------------------------------------------

def convert_alpha_comparison(function,reference):
    if function == gx.CompareFunction.NEVER:
        return 'false'
    if function == gx.CompareFunction.LESS:
        return 'tevprev.a <= {} - 0.25/255.0'.format(reference/255)
    if function == gx.CompareFunction.EQUAL:
        return 'abs(tevprev.a - {}) < 0.5/255.0'.format(reference/255)
    if function == gx.CompareFunction.LEQUAL:
        return 'tevprev.a < {} + 0.25/255.0'.format(reference/255)
    if function == gx.CompareFunction.GREATER:
        return 'tevprev.a >= {} + 0.25/255.0'.format(reference/255)
    if function == gx.CompareFunction.NEQUAL:
        return 'abs(tevprev.a - {}) >= 0.5/255.0'.format(reference/255)
    if function == gx.CompareFunction.GEQUAL:
        return 'tevprev.a > {} - 0.25/255.0'.format(reference/255)
    if function == gx.CompareFunction.ALWAYS:
        return 'true'

    raise ValueError('invalid alpha compare function') #<-?


def convert_alpha_test_operator(operator):
    if operator == gx.AOP_AND:
        return '&&'
    if operator == gx.AOP_OR:
        return '||'
    if operator == gx.AOP_XOR:
        return '!='
    if operator == gx.AOP_XNOR:
        return '=='

    raise ValueError('invalid alpha test operator')


def write_alpha_test(stream,test):
    if test.operator == gx.AOP_AND:
        never_pass = test.function0 == gx.CompareFunction.NEVER or test.function1 == gx.CompareFunction.NEVER
        always_pass = test.function0 == test.function1 == gx.CompareFunction.ALWAYS
    elif test.operator == gx.AOP_OR:
        never_pass = test.function0 == test.function1 == gx.CompareFunction.NEVER
        always_pass = test.function0 == gx.CompareFunction.ALWAYS or test.function1 == gx.CompareFunction.ALWAYS
    elif test.operator == gx.AOP_XOR:
        never_pass = test.function0 == test.function1 in {gx.CompareFunction.NEVER,gx.CompareFunction.ALWAYS}
        always_pass = {test.function0,test.function1} == {gx.CompareFunction.NEVER,gx.CompareFunction.ALWAYS}
    elif test.operator == gx.AOP_XNOR:
        never_pass = {test.function0,test.function1} == {gx.CompareFunction.NEVER,gx.CompareFunction.ALWAYS}
        always_pass = test.function0 == test.function1 in {gx.CompareFunction.NEVER,gx.CompareFunction.ALWAYS}

    if always_pass:
        return

    if never_pass:
        stream.write('discard;\n')
        return

    comparison0 = convert_alpha_comparison(test.function0,test.reference0)
    comparison1 = convert_alpha_comparison(test.function1,test.reference1)
    operator = convert_alpha_test_operator(test.operator)
    stream.write('if ( !(({}) {} ({})) ){{\n'.format(comparison0,operator,comparison1))
    stream.write('    discard;}\n')


def create_shader_string(material):
    stream = StringIO()

    stream.write('#version 330\n')

    if material.depth_test_early and glInitShaderImageLoadStoreARB():
        # This doesn't force the driver to write to the depth buffer
        # if the alpha test fails, it just allows it
        stream.write('#extension GL_ARB_shader_image_load_store : enable\n')
        stream.write('layout(early_fragment_tests) in;\n')

    stream.write('{}\n'.format(material.gl_block.glsl_type))

    for i in range(2):
        if i < material.channel_count:
            stream.write('in vec4 channel{};\n'.format(i))
        else:
            stream.write('const vec4 channel{} = vec4(1.0);\n'.format(i))

    for i,generator in enumerate(material.enabled_texcoord_generators):
        stream.write('in vec3 generated_texcoord{};\n'.format(i))

    use_texture = [False]*8
    for stage in material.enabled_tev_stages:
        if stage.texture != gx.TEXMAP_NULL:
            texture_index = gx.TEXMAP.index(stage.texture)
            use_texture[texture_index] = True
    for stage in material.enabled_indirect_stages:
        if stage.texture != gx.TEXMAP_NULL:
            texture_index = gx.TEXMAP.index(stage.texture)
            use_texture[texture_index] = True

    for i in range(8):
        if not use_texture[i]: continue
        stream.write('uniform sampler2D texmap{};\n'.format(i))

    stream.write('out vec4 fragment_color;\n')

    stream.write('\nvoid main()\n{\n')
    stream.write('float alphabump;\n')
    stream.write('vec3 indtevcrd;\n')
    stream.write('vec2 indtevtrans;\n')
    stream.write('vec2 wrappedcoord;\n')
    stream.write('vec2 tevcoord;\n')
    stream.write('vec4 textemp;\n')

    for i in range(8):
        if i < material.texcoord_generator_count:
            stream.write('vec2 uv{} = generated_texcoord{}.st'.format(i,i))
            if generator.function == gx.TG_MTX3x4:
                stream.write('/generated_texcoord{}.p'.format(i))
            stream.write(';\n')
        else:
            stream.write('const vec2 uv{} = vec2(1.0);\n'.format(i))

    stream.write('vec4 tevprev = tev_color_previous;\n')

    for i in range(3):
        stream.write('vec4 tevreg{} = tev_color{};\n'.format(i,i))

    for i,stage in enumerate(material.indirect_stages):
        if i >= material.indirect_stage_count or stage.texcoord == gx.TEXCOORD_NULL or stage.texture == gx.TEXMAP_NULL:
            stream.write('vec3 indtex{} = vec3(0.0);'.format(i))
            continue
        write_indirect_stage(stream,i,stage)

    for i,stage in enumerate(material.enabled_tev_stages):
        stream.write('\n// TEV stage {}\n'.format(i))
        write_tev_stage(stream,stage,material)

    stream.write('tevprev = fract(tevprev*(255.0/256.0))*(256.0/255.0);\n\n')

    write_alpha_test(stream,material.alpha_test)

    stream.write('fragment_color = tevprev;\n')
    stream.write('}\n')

    return stream.getvalue()

