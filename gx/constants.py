import enum
import numpy
from OpenGL.GL import *


class Value(int):

    def __new__(cls,value,*args,**kwargs):
        return super().__new__(cls,value)

    def __init__(self,value,**attributes):
        self.attributes = attributes


class Enum(int,enum.Enum):

    def __init__(self,value):
        if hasattr(value,'attributes'):
            for attribute in value.attributes.items():
                setattr(self,*attribute)


class ExtendEnumMeta(enum.EnumMeta):

    def __new__(metacls,cls,bases,classdict):
        (base_enum,) = bases
        enum_class = super().__new__(metacls,cls,base_enum.__bases__,classdict)
        enum_class.base_enum = base_enum
        return enum_class

    #TODO: __dir__

    def __call__(self,*args,**kwargs):
        try:
            return self.base_enum(*args,**kwargs)
        except ValueError:
            return super().__call__(*args,**kwargs)

    def __getattr__(self,name):
        try:
            return getattr(self.base_enum,name)
        except AttributeError:
            return super().__getattr__(name)

    def __getitem__(self,name):
        try:
            return self.base_enum[name]
        except KeyError:
            return super().__getitem__(name)

    def __contains__(self,member):
        return member in self.base_enum or super().__contains__(member)

    def __len__(self):
        return len(self.base_enum) + super().__len__()

    def __iter__(self):
        yield from self.base_enum
        yield from super().__iter__()

    def __reversed__(self):
        yield from super().__reversed__()
        yield from reversed(self.base_enum)

    #TODO: __members__


class Attribute(Enum):
    VA_PTNMTXIDX = 0
    VA_TEX0MTXIDX = Value(1,index=0)
    VA_TEX1MTXIDX = Value(2,index=1)
    VA_TEX2MTXIDX = Value(3,index=2)
    VA_TEX3MTXIDX = Value(4,index=3)
    VA_TEX4MTXIDX = Value(5,index=4)
    VA_TEX5MTXIDX = Value(6,index=5)
    VA_TEX6MTXIDX = Value(7,index=6)
    VA_TEX7MTXIDX = Value(8,index=7)
    VA_POS = 9
    VA_NRM = 10
    VA_CLR0 = Value(11,index=0)
    VA_CLR1 = Value(12,index=1)
    VA_TEX0 = Value(13,index=0)
    VA_TEX1 = Value(14,index=1)
    VA_TEX2 = Value(15,index=2)
    VA_TEX3 = Value(16,index=3)
    VA_TEX4 = Value(17,index=4)
    VA_TEX5 = Value(18,index=5)
    VA_TEX6 = Value(19,index=6)
    VA_TEX7 = Value(20,index=7)
    POSMTXARRAY = 21
    NRMMTXARRAY = 22
    TEXMTXARRAY = 23
    LIGHTARRAY = 24
    VA_NBT = 25
    VA_NULL = 0xFF


VA_PTNMTXIDX = Attribute.VA_PTNMTXIDX
VA_TEX0MTXIDX = Attribute.VA_TEX0MTXIDX
VA_TEX1MTXIDX = Attribute.VA_TEX1MTXIDX
VA_TEX2MTXIDX = Attribute.VA_TEX2MTXIDX
VA_TEX3MTXIDX = Attribute.VA_TEX3MTXIDX
VA_TEX4MTXIDX = Attribute.VA_TEX4MTXIDX
VA_TEX5MTXIDX = Attribute.VA_TEX5MTXIDX
VA_TEX6MTXIDX = Attribute.VA_TEX6MTXIDX
VA_TEX7MTXIDX = Attribute.VA_TEX7MTXIDX
VA_TEXMTXIDX = [VA_TEX0MTXIDX,VA_TEX1MTXIDX,VA_TEX2MTXIDX,VA_TEX3MTXIDX,VA_TEX4MTXIDX,VA_TEX5MTXIDX,VA_TEX6MTXIDX,VA_TEX7MTXIDX]
VA_POS = Attribute.VA_POS
VA_NRM = Attribute.VA_NRM
VA_CLR0 = Attribute.VA_CLR0
VA_CLR1 = Attribute.VA_CLR1
VA_CLR = [VA_CLR0,VA_CLR1]
VA_TEX0 = Attribute.VA_TEX0
VA_TEX1 = Attribute.VA_TEX1
VA_TEX2 = Attribute.VA_TEX2
VA_TEX3 = Attribute.VA_TEX3
VA_TEX4 = Attribute.VA_TEX4
VA_TEX5 = Attribute.VA_TEX5
VA_TEX6 = Attribute.VA_TEX6
VA_TEX7 = Attribute.VA_TEX7
VA_TEX = [VA_TEX0,VA_TEX1,VA_TEX2,VA_TEX3,VA_TEX4,VA_TEX5,VA_TEX6,VA_TEX7]
POSMTXARRAY = Attribute.POSMTXARRAY
NRMMTXARRAY = Attribute.NRMMTXARRAY
TEXMTXARRAY = Attribute.TEXMTXARRAY
LIGHTARRAY = Attribute.LIGHTARRAY
VA_NBT = Attribute.VA_NBT
VA_NULL = Attribute.VA_NULL


class ComponentType(Enum):
    U8 = Value(0,numpy_type=numpy.uint8)
    S8 = Value(1,numpy_type=numpy.int8)
    U16 = Value(2,numpy_type=numpy.uint16)
    S16 = Value(3,numpy_type=numpy.int16)
    F32 = Value(4,numpy_type=numpy.float32)


U8 = ComponentType.U8
S8 = ComponentType.S8
U16 = ComponentType.U16
S16 = ComponentType.S16
F32 = ComponentType.F32


class ColorComponentType(Enum):
    RGB565 = 0
    RGB8 = 1
    RGBX8 = 2
    RGBA4 = 3
    RGBA6 = 4
    RGBA8 = 5


RGB565 = ColorComponentType.RGB565
RGB8 = ColorComponentType.RGB8
RGBX8 = ColorComponentType.RGBX8
RGBA4 = ColorComponentType.RGBA4
RGBA6 = ColorComponentType.RGBA6
RGBA8 = ColorComponentType.RGBA8


class PositionComponentCount(Enum):
    POS_XY = Value(0,actual_value=2)
    POS_XYZ = Value(1,actual_value=3)


POS_XY = PositionComponentCount.POS_XY
POS_XYZ = PositionComponentCount.POS_XYZ


class NormalComponentCount(Enum):
    NRM_XYZ = Value(0,actual_value=3)
    NRM_NBT = 1
    NRM_NBT3 = 2


NRM_XYZ = NormalComponentCount.NRM_XYZ
NRM_NBT = NormalComponentCount.NRM_NBT
NRM_NBT3 = NormalComponentCount.NRM_NBT3


class ColorComponentCount(Enum):
    CLR_RGB = 0
    CLR_RGBA = 1


CLR_RGB = ColorComponentCount.CLR_RGB
CLR_RGBA = ColorComponentCount.CLR_RGBA


class TexCoordComponentCount(Enum):
    TEX_S = Value(0,actual_value=1)
    TEX_ST = Value(1,actual_value=2)


TEX_S = TexCoordComponentCount.TEX_S
TEX_ST = TexCoordComponentCount.TEX_ST


class InputType(Enum):
    NONE = 0
    DIRECT = 1
    INDEX8 = 2
    INDEX16 = 3


NONE = InputType.NONE
DIRECT = InputType.DIRECT
INDEX8 = InputType.INDEX8
INDEX16 = InputType.INDEX16


class PrimitiveType(Enum):
    POINTS = 0xB8
    LINES = 0xA8
    LINESTRIP = 0xB0
    TRIANGLES = 0x90
    TRIANGLESTRIP = 0x98
    TRIANGLEFAN = 0xA0
    QUADS = 0x80


POINTS = PrimitiveType.POINTS
LINES = PrimitiveType.LINES
LINESTRIP = PrimitiveType.LINESTRIP
TRIANGLES = PrimitiveType.TRIANGLES
TRIANGLESTRIP = PrimitiveType.TRIANGLESTRIP
TRIANGLEFAN = PrimitiveType.TRIANGLEFAN
QUADS = PrimitiveType.QUADS


class Channel(Enum):
    COLOR0 = Value(0,index=0)
    COLOR1 = Value(1,index=1)
    ALPHA0 = Value(2,index=0)
    ALPHA1 = Value(3,index=1)
    COLOR0A0 = Value(4,index=0)
    COLOR1A1 = Value(5,index=1)
    COLOR_ZERO = 6
    ALPHA_BUMP = 7
    ALPHA_BUMPN = 8
    COLOR_NULL = 0xFF


COLOR0 = Channel.COLOR0
COLOR1 = Channel.COLOR1
COLOR = [COLOR0,COLOR1]
ALPHA0 = Channel.ALPHA0
ALPHA1 = Channel.ALPHA1
ALPHA = [ALPHA0,ALPHA1]
COLOR0A0 = Channel.COLOR0A0
COLOR1A1 = Channel.COLOR1A1
COLOR_ZERO = Channel.COLOR_ZERO
ALPHA_BUMP = Channel.ALPHA_BUMP
ALPHA_BUMPN = Channel.ALPHA_BUMPN
COLOR_NULL = Channel.COLOR_NULL


class ChannelSource(Enum):
    SRC_REG = 0
    SRC_VTX = 1


SRC_REG = ChannelSource.SRC_REG
SRC_VTX = ChannelSource.SRC_VTX


class Light(Enum):
    LIGHT0 = Value(0x01,index=0)
    LIGHT1 = Value(0x02,index=0)
    LIGHT2 = Value(0x04,index=0)
    LIGHT3 = Value(0x08,index=0)
    LIGHT4 = Value(0x10,index=0)
    LIGHT5 = Value(0x20,index=0)
    LIGHT6 = Value(0x40,index=0)
    LIGHT7 = Value(0x80,index=0)
    LIGHT_NULL = 0x00


LIGHT0 = Light.LIGHT0
LIGHT1 = Light.LIGHT1
LIGHT2 = Light.LIGHT2
LIGHT3 = Light.LIGHT3
LIGHT4 = Light.LIGHT4
LIGHT5 = Light.LIGHT5
LIGHT6 = Light.LIGHT6
LIGHT7 = Light.LIGHT7
LIGHT = [LIGHT0,LIGHT1,LIGHT2,LIGHT3,LIGHT4,LIGHT5,LIGHT6,LIGHT7]
LIGHT_NULL = Light.LIGHT_NULL


class DiffuseFunction(Enum):
    DF_NONE = 0
    DF_SIGNED = 1
    DF_CLAMP = 2


DF_NONE = DiffuseFunction.DF_NONE
DF_SIGNED = DiffuseFunction.DF_SIGNED
DF_CLAMP = DiffuseFunction.DF_CLAMP


class AttenuationFunction(Enum):
    AF_SPEC = 0
    AF_SPOT = 1
    AF_NONE = 2


AF_SPEC = AttenuationFunction.AF_SPEC
AF_SPOT = AttenuationFunction.AF_SPOT
AF_NONE = AttenuationFunction.AF_NONE


class TexCoord(Enum):
    TEXCOORD0 = Value(0,index=0)
    TEXCOORD1 = Value(1,index=1)
    TEXCOORD2 = Value(2,index=2)
    TEXCOORD3 = Value(3,index=3)
    TEXCOORD4 = Value(4,index=4)
    TEXCOORD5 = Value(5,index=5)
    TEXCOORD6 = Value(6,index=6)
    TEXCOORD7 = Value(7,index=7)
    TEXCOORD_NULL = 0xFF


TEXCOORD0 = TexCoord.TEXCOORD0
TEXCOORD1 = TexCoord.TEXCOORD1
TEXCOORD2 = TexCoord.TEXCOORD2
TEXCOORD3 = TexCoord.TEXCOORD3
TEXCOORD4 = TexCoord.TEXCOORD4
TEXCOORD5 = TexCoord.TEXCOORD5
TEXCOORD6 = TexCoord.TEXCOORD6
TEXCOORD7 = TexCoord.TEXCOORD7
TEXCOORD = [TEXCOORD0,TEXCOORD1,TEXCOORD2,TEXCOORD3,TEXCOORD4,TEXCOORD5,TEXCOORD6,TEXCOORD7]
TEXCOORD_NULL = TexCoord.TEXCOORD_NULL


class TexCoordFunction(Enum):
    TG_MTX3x4 = 0
    TG_MTX2x4 = 1
    TG_BUMP0 = Value(2,index=0)
    TG_BUMP1 = Value(3,index=1)
    TG_BUMP2 = Value(4,index=2)
    TG_BUMP3 = Value(5,index=3)
    TG_BUMP4 = Value(6,index=4)
    TG_BUMP5 = Value(7,index=5)
    TG_BUMP6 = Value(8,index=6)
    TG_BUMP7 = Value(9,index=7)
    TG_SRTG = 10


TG_MTX3x4 = TexCoordFunction.TG_MTX3x4
TG_MTX2x4 = TexCoordFunction.TG_MTX2x4
TG_BUMP0 = TexCoordFunction.TG_BUMP0
TG_BUMP1 = TexCoordFunction.TG_BUMP1
TG_BUMP2 = TexCoordFunction.TG_BUMP2
TG_BUMP3 = TexCoordFunction.TG_BUMP3
TG_BUMP4 = TexCoordFunction.TG_BUMP4
TG_BUMP5 = TexCoordFunction.TG_BUMP5
TG_BUMP6 = TexCoordFunction.TG_BUMP6
TG_BUMP7 = TexCoordFunction.TG_BUMP7
TG_BUMP = [TG_BUMP0,TG_BUMP1,TG_BUMP2,TG_BUMP3,TG_BUMP4,TG_BUMP5,TG_BUMP6,TG_BUMP7]
TG_SRTG = TexCoordFunction.TG_SRTG


class TexCoordSource(Enum):
    TG_POS = 0
    TG_NRM = 1
    TG_BINRM = 2
    TG_TANGENT = 3
    TG_TEX0 = Value(4,index=0)
    TG_TEX1 = Value(5,index=1)
    TG_TEX2 = Value(6,index=2)
    TG_TEX3 = Value(7,index=3)
    TG_TEX4 = Value(8,index=4)
    TG_TEX5 = Value(9,index=5)
    TG_TEX6 = Value(10,index=6)
    TG_TEX7 = Value(11,index=7)
    TG_TEXCOORD0 = Value(12,index=0)
    TG_TEXCOORD1 = Value(13,index=1)
    TG_TEXCOORD2 = Value(14,index=2)
    TG_TEXCOORD3 = Value(15,index=3)
    TG_TEXCOORD4 = Value(16,index=4)
    TG_TEXCOORD5 = Value(17,index=5)
    TG_TEXCOORD6 = Value(18,index=6)
    TG_COLOR0 = Value(19,index=0)
    TG_COLOR1 = Value(20,index=1)


TG_POS = TexCoordSource.TG_POS
TG_NRM = TexCoordSource.TG_NRM
TG_BINRM = TexCoordSource.TG_BINRM
TG_TANGENT = TexCoordSource.TG_TANGENT
TG_TEX0 = TexCoordSource.TG_TEX0
TG_TEX1 = TexCoordSource.TG_TEX1
TG_TEX2 = TexCoordSource.TG_TEX2
TG_TEX3 = TexCoordSource.TG_TEX3
TG_TEX4 = TexCoordSource.TG_TEX4
TG_TEX5 = TexCoordSource.TG_TEX5
TG_TEX6 = TexCoordSource.TG_TEX6
TG_TEX7 = TexCoordSource.TG_TEX7
TG_TEX = [TG_TEX0,TG_TEX1,TG_TEX2,TG_TEX3,TG_TEX4,TG_TEX5,TG_TEX6,TG_TEX7]
TG_TEXCOORD0 = TexCoordSource.TG_TEXCOORD0
TG_TEXCOORD1 = TexCoordSource.TG_TEXCOORD1
TG_TEXCOORD2 = TexCoordSource.TG_TEXCOORD2
TG_TEXCOORD3 = TexCoordSource.TG_TEXCOORD3
TG_TEXCOORD4 = TexCoordSource.TG_TEXCOORD4
TG_TEXCOORD5 = TexCoordSource.TG_TEXCOORD5
TG_TEXCOORD6 = TexCoordSource.TG_TEXCOORD6
TG_TEXCOORD = [TG_TEXCOORD0,TG_TEXCOORD1,TG_TEXCOORD2,TG_TEXCOORD3,TG_TEXCOORD4,TG_TEXCOORD5,TG_TEXCOORD6]
TG_COLOR0 = TexCoordSource.TG_COLOR0
TG_COLOR1 = TexCoordSource.TG_COLOR1
TG_COLOR = [TG_COLOR0,TG_COLOR1]


class TextureMatrix(Enum):
    TEXMTX0 = Value(30,index=0)
    TEXMTX1 = Value(33,index=1)
    TEXMTX2 = Value(36,index=2)
    TEXMTX3 = Value(39,index=3)
    TEXMTX4 = Value(42,index=4)
    TEXMTX5 = Value(45,index=5)
    TEXMTX6 = Value(48,index=6)
    TEXMTX7 = Value(51,index=7)
    TEXMTX8 = Value(54,index=8)
    TEXMTX9 = Value(57,index=9)
    IDENTITY = 60


TEXMTX0 = TextureMatrix.TEXMTX0
TEXMTX1 = TextureMatrix.TEXMTX1
TEXMTX2 = TextureMatrix.TEXMTX2
TEXMTX3 = TextureMatrix.TEXMTX3
TEXMTX4 = TextureMatrix.TEXMTX4
TEXMTX5 = TextureMatrix.TEXMTX5
TEXMTX6 = TextureMatrix.TEXMTX6
TEXMTX7 = TextureMatrix.TEXMTX7
TEXMTX8 = TextureMatrix.TEXMTX8
TEXMTX9 = TextureMatrix.TEXMTX9
TEXMTX = [TEXMTX0,TEXMTX1,TEXMTX2,TEXMTX3,TEXMTX4,TEXMTX5,TEXMTX6,TEXMTX7,TEXMTX8,TEXMTX9]
IDENTITY = TextureMatrix.IDENTITY


class PostTransformMatrix(Enum):
    PTTMTX0 = Value(64,index=0)
    PTTMTX1 = Value(67,index=1)
    PTTMTX2 = Value(70,index=2)
    PTTMTX3 = Value(73,index=3)
    PTTMTX4 = Value(76,index=4)
    PTTMTX5 = Value(79,index=5)
    PTTMTX6 = Value(82,index=6)
    PTTMTX7 = Value(85,index=7)
    PTTMTX8 = Value(88,index=8)
    PTTMTX9 = Value(91,index=9)
    PTTMTX10 = Value(94,index=10)
    PTTMTX11 = Value(97,index=11)
    PTTMTX12 = Value(100,index=12)
    PTTMTX13 = Value(103,index=13)
    PTTMTX14 = Value(106,index=14)
    PTTMTX15 = Value(109,index=15)
    PTTMTX16 = Value(112,index=16)
    PTTMTX17 = Value(115,index=17)
    PTTMTX18 = Value(118,index=18)
    PTTMTX19 = Value(121,index=19)
    PTTIDENTITY = 125


PTTMTX0 = PostTransformMatrix.PTTMTX0
PTTMTX1 = PostTransformMatrix.PTTMTX1
PTTMTX2 = PostTransformMatrix.PTTMTX2
PTTMTX3 = PostTransformMatrix.PTTMTX3
PTTMTX4 = PostTransformMatrix.PTTMTX4
PTTMTX5 = PostTransformMatrix.PTTMTX5
PTTMTX6 = PostTransformMatrix.PTTMTX6
PTTMTX7 = PostTransformMatrix.PTTMTX7
PTTMTX8 = PostTransformMatrix.PTTMTX8
PTTMTX9 = PostTransformMatrix.PTTMTX9
PTTMTX10 = PostTransformMatrix.PTTMTX10
PTTMTX11 = PostTransformMatrix.PTTMTX11
PTTMTX12 = PostTransformMatrix.PTTMTX12
PTTMTX13 = PostTransformMatrix.PTTMTX13
PTTMTX14 = PostTransformMatrix.PTTMTX14
PTTMTX15 = PostTransformMatrix.PTTMTX15
PTTMTX16 = PostTransformMatrix.PTTMTX16
PTTMTX17 = PostTransformMatrix.PTTMTX17
PTTMTX18 = PostTransformMatrix.PTTMTX18
PTTMTX19 = PostTransformMatrix.PTTMTX19
PTTMTX = [PTTMTX0,PTTMTX1,PTTMTX2,PTTMTX3,PTTMTX4,PTTMTX5,PTTMTX6,PTTMTX7,PTTMTX8,PTTMTX9,PTTMTX10,PTTMTX11,PTTMTX12,PTTMTX13,PTTMTX14,PTTMTX15,PTTMTX16,PTTMTX17,PTTMTX18,PTTMTX19]
PTTIDENTITY = PostTransformMatrix.PTTIDENTITY


class Texture(Enum):
    TEXMAP0 = Value(0,index=0)
    TEXMAP1 = Value(1,index=1)
    TEXMAP2 = Value(2,index=2)
    TEXMAP3 = Value(3,index=3)
    TEXMAP4 = Value(4,index=4)
    TEXMAP5 = Value(5,index=5)
    TEXMAP6 = Value(6,index=6)
    TEXMAP7 = Value(7,index=7)
    TEXMAP_NULL = 0xFF
    TEXMAP_DISABLE = 0x100


TEXMAP0 = Texture.TEXMAP0
TEXMAP1 = Texture.TEXMAP1
TEXMAP2 = Texture.TEXMAP2
TEXMAP3 = Texture.TEXMAP3
TEXMAP4 = Texture.TEXMAP4
TEXMAP5 = Texture.TEXMAP5
TEXMAP6 = Texture.TEXMAP6
TEXMAP7 = Texture.TEXMAP7
TEXMAP = [TEXMAP0,TEXMAP1,TEXMAP2,TEXMAP3,TEXMAP4,TEXMAP5,TEXMAP6,TEXMAP7]
TEXMAP_NULL = Texture.TEXMAP_NULL
TEXMAP_DISABLE = Texture.TEXMAP_DISABLE


class TextureFormat(Enum):
    TF_I4 = 0
    TF_I8 = 1
    TF_IA4 = 2
    TF_IA8 = 3
    TF_RGB565 = 4
    TF_RGB5A3 = 5
    TF_RGBA8 = 6
    TF_CI4 = 8
    TF_CI8 = 9
    TF_CI14 = 10
    TF_CMPR = 14


TF_I4 = TextureFormat.TF_I4
TF_I8 = TextureFormat.TF_I8
TF_IA4 = TextureFormat.TF_IA4
TF_IA8 = TextureFormat.TF_IA8
TF_RGB565 = TextureFormat.TF_RGB565
TF_RGB5A3 = TextureFormat.TF_RGB5A3
TF_RGBA8 = TextureFormat.TF_RGBA8
TF_CI4 = TextureFormat.TF_CI4
TF_CI8 = TextureFormat.TF_CI8
TF_CI14 = TextureFormat.TF_CI14
TF_CMPR = TextureFormat.TF_CMPR


class PaletteFormat(Enum):
    TL_IA8 = 0
    TL_RGB565 = 1
    TL_RGB5A3 = 2


TL_IA8 = PaletteFormat.TL_IA8
TL_RGB565 = PaletteFormat.TL_RGB565
TL_RGB5A3 = PaletteFormat.TL_RGB5A3


class WrapMode(Enum):
    CLAMP = Value(0,gl_value=GL_CLAMP_TO_EDGE)
    REPEAT = Value(1,gl_value=GL_REPEAT)
    MIRROR = Value(2,gl_value=GL_MIRRORED_REPEAT)


CLAMP = WrapMode.CLAMP
REPEAT = WrapMode.REPEAT
MIRROR = WrapMode.MIRROR


class FilterMode(Enum):
    NEAR = Value(0,gl_value=GL_NEAREST)
    LINEAR = Value(1,gl_value=GL_LINEAR)
    NEAR_MIP_NEAR = Value(2,gl_value=GL_NEAREST_MIPMAP_NEAREST)
    LIN_MIP_NEAR = Value(3,gl_value=GL_LINEAR_MIPMAP_NEAREST)
    NEAR_MIP_LIN = Value(4,gl_value=GL_NEAREST_MIPMAP_LINEAR)
    LIN_MIP_LIN = Value(5,gl_value=GL_LINEAR_MIPMAP_LINEAR)


NEAR = FilterMode.NEAR
LINEAR = FilterMode.LINEAR
NEAR_MIP_NEAR = FilterMode.NEAR_MIP_NEAR
LIN_MIP_NEAR = FilterMode.LIN_MIP_NEAR
NEAR_MIP_LIN = FilterMode.NEAR_MIP_LIN
LIN_MIP_LIN = FilterMode.LIN_MIP_LIN


class TevStage(Enum):
    TEVSTAGE0 = Value(0,index=0)
    TEVSTAGE1 = Value(1,index=1)
    TEVSTAGE2 = Value(2,index=2)
    TEVSTAGE3 = Value(3,index=3)
    TEVSTAGE4 = Value(4,index=4)
    TEVSTAGE5 = Value(5,index=5)
    TEVSTAGE6 = Value(6,index=6)
    TEVSTAGE7 = Value(7,index=7)
    TEVSTAGE8 = Value(8,index=8)
    TEVSTAGE9 = Value(9,index=9)
    TEVSTAGE10 = Value(10,index=10)
    TEVSTAGE11 = Value(11,index=11)
    TEVSTAGE12 = Value(12,index=12)
    TEVSTAGE13 = Value(13,index=13)
    TEVSTAGE14 = Value(14,index=14)
    TEVSTAGE15 = Value(15,index=15)


TEVSTAGE0 = TevStage.TEVSTAGE0
TEVSTAGE1 = TevStage.TEVSTAGE1
TEVSTAGE2 = TevStage.TEVSTAGE2
TEVSTAGE3 = TevStage.TEVSTAGE3
TEVSTAGE4 = TevStage.TEVSTAGE4
TEVSTAGE5 = TevStage.TEVSTAGE5
TEVSTAGE6 = TevStage.TEVSTAGE6
TEVSTAGE7 = TevStage.TEVSTAGE7
TEVSTAGE8 = TevStage.TEVSTAGE8
TEVSTAGE9 = TevStage.TEVSTAGE9
TEVSTAGE10 = TevStage.TEVSTAGE10
TEVSTAGE11 = TevStage.TEVSTAGE11
TEVSTAGE12 = TevStage.TEVSTAGE12
TEVSTAGE13 = TevStage.TEVSTAGE13
TEVSTAGE14 = TevStage.TEVSTAGE14
TEVSTAGE15 = TevStage.TEVSTAGE15
TEVSTAGE = [TEVSTAGE0,TEVSTAGE1,TEVSTAGE2,TEVSTAGE3,TEVSTAGE4,TEVSTAGE5,TEVSTAGE6,TEVSTAGE7,TEVSTAGE8,TEVSTAGE9,TEVSTAGE10,TEVSTAGE11,TEVSTAGE12,TEVSTAGE13,TEVSTAGE14,TEVSTAGE15]


class ColorInput(Enum):
    CC_CPREV = 0
    CC_APREV = 1
    CC_C0 = 2
    CC_A0 = 3
    CC_C1 = 4
    CC_A1 = 5
    CC_C2 = 6
    CC_A2 = 7
    CC_TEXC = 8
    CC_TEXA = 9
    CC_RASC = 10
    CC_RASA = 11
    CC_ONE = 12
    CC_HALF = 13
    CC_KONST = 14
    CC_ZERO = 15


CC_CPREV = ColorInput.CC_CPREV
CC_APREV = ColorInput.CC_APREV
CC_C0 = ColorInput.CC_C0
CC_A0 = ColorInput.CC_A0
CC_C1 = ColorInput.CC_C1
CC_A1 = ColorInput.CC_A1
CC_C2 = ColorInput.CC_C2
CC_A2 = ColorInput.CC_A2
CC_TEXC = ColorInput.CC_TEXC
CC_TEXA = ColorInput.CC_TEXA
CC_RASC = ColorInput.CC_RASC
CC_RASA = ColorInput.CC_RASA
CC_ONE = ColorInput.CC_ONE
CC_HALF = ColorInput.CC_HALF
CC_KONST = ColorInput.CC_KONST
CC_ZERO = ColorInput.CC_ZERO


class AlphaInput(Enum):
    CA_APREV = 0
    CA_A0 = 1
    CA_A1 = 2
    CA_A2 = 3
    CA_TEXA = 4
    CA_RASA = 5
    CA_KONST = 6
    CA_ZERO = 7


CA_APREV = AlphaInput.CA_APREV
CA_A0 = AlphaInput.CA_A0
CA_A1 = AlphaInput.CA_A1
CA_A2 = AlphaInput.CA_A2
CA_TEXA = AlphaInput.CA_TEXA
CA_RASA = AlphaInput.CA_RASA
CA_KONST = AlphaInput.CA_KONST
CA_ZERO = AlphaInput.CA_ZERO


class TevFunction(Enum):
    TEV_ADD = 0
    TEV_SUB = 1
    TEV_COMP_R8_GT = 8
    TEV_COMP_R8_EQ = 9
    TEV_COMP_GR16_GT = 10
    TEV_COMP_GR16_EQ = 11
    TEV_COMP_BGR24_GT = 12
    TEV_COMP_BGR24_EQ = 13
    TEV_COMP_RGB8_GT = 14
    TEV_COMP_RGB8_EQ = 15
    TEV_COMP_A8_GT = TEV_COMP_RGB8_GT
    TEV_COMP_A8_EQ = TEV_COMP_RGB8_EQ


TEV_ADD = TevFunction.TEV_ADD
TEV_SUB = TevFunction.TEV_SUB
TEV_COMP_R8_GT = TevFunction.TEV_COMP_R8_GT
TEV_COMP_R8_EQ = TevFunction.TEV_COMP_R8_EQ
TEV_COMP_GR16_GT = TevFunction.TEV_COMP_GR16_GT
TEV_COMP_GR16_EQ = TevFunction.TEV_COMP_GR16_EQ
TEV_COMP_BGR24_GT = TevFunction.TEV_COMP_BGR24_GT
TEV_COMP_BGR24_EQ = TevFunction.TEV_COMP_BGR24_EQ
TEV_COMP_RGB8_GT = TevFunction.TEV_COMP_RGB8_GT
TEV_COMP_RGB8_EQ = TevFunction.TEV_COMP_RGB8_EQ
TEV_COMP_A8_GT = TevFunction.TEV_COMP_A8_GT
TEV_COMP_A8_EQ = TevFunction.TEV_COMP_A8_EQ


class TevBias(Enum):
    TB_ZERO = 0
    TB_ADDHALF = 1
    TB_SUBHALF = 2
    TB_UNKNOWN0 = 3


TB_ZERO = TevBias.TB_ZERO
TB_ADDHALF = TevBias.TB_ADDHALF
TB_SUBHALF = TevBias.TB_SUBHALF
TB_UNKNOWN0 = TevBias.TB_UNKNOWN0


class TevScale(Enum):
    CS_SCALE_1 = 0
    CS_SCALE_2 = 1
    CS_SCALE_4 = 2
    CS_DIVIDE_2 = 3


CS_SCALE_1 = TevScale.CS_SCALE_1
CS_SCALE_2 = TevScale.CS_SCALE_2
CS_SCALE_4 = TevScale.CS_SCALE_4
CS_DIVIDE_2 = TevScale.CS_DIVIDE_2


class TevColor(Enum):
    TEVPREV = 0
    TEVREG0 = Value(1,index=0)
    TEVREG1 = Value(2,index=1)
    TEVREG2 = Value(3,index=2)


TEVPREV = TevColor.TEVPREV
TEVREG0 = TevColor.TEVREG0
TEVREG1 = TevColor.TEVREG1
TEVREG2 = TevColor.TEVREG2
TEVREG = [TEVREG0,TEVREG1,TEVREG2]


class KColor(Enum):
    KCOLOR0 = Value(0,index=0)
    KCOLOR1 = Value(1,index=1)
    KCOLOR2 = Value(2,index=2)
    KCOLOR3 = Value(3,index=3)


KCOLOR0 = KColor.KCOLOR0
KCOLOR1 = KColor.KCOLOR1
KCOLOR2 = KColor.KCOLOR2
KCOLOR3 = KColor.KCOLOR3
KCOLOR = [KCOLOR0,KCOLOR1,KCOLOR2,KCOLOR3]


class ConstantColor(Enum):
    TEV_KCSEL_1 = 0
    TEV_KCSEL_7_8 = 1
    TEV_KCSEL_3_4 = 2
    TEV_KCSEL_5_8 = 3
    TEV_KCSEL_1_2 = 4
    TEV_KCSEL_3_8 = 5
    TEV_KCSEL_1_4 = 6
    TEV_KCSEL_1_8 = 7
    TEV_KCSEL_K0 = 12
    TEV_KCSEL_K1 = 13
    TEV_KCSEL_K2 = 14
    TEV_KCSEL_K3 = 15
    TEV_KCSEL_K0_R = 16
    TEV_KCSEL_K1_R = 17
    TEV_KCSEL_K2_R = 18
    TEV_KCSEL_K3_R = 19
    TEV_KCSEL_K0_G = 20
    TEV_KCSEL_K1_G = 21
    TEV_KCSEL_K2_G = 22
    TEV_KCSEL_K3_G = 23
    TEV_KCSEL_K0_B = 24
    TEV_KCSEL_K1_B = 25
    TEV_KCSEL_K2_B = 26
    TEV_KCSEL_K3_B = 27
    TEV_KCSEL_K0_A = 28
    TEV_KCSEL_K1_A = 29
    TEV_KCSEL_K2_A = 30
    TEV_KCSEL_K3_A = 31


TEV_KCSEL_1 = ConstantColor.TEV_KCSEL_1
TEV_KCSEL_7_8 = ConstantColor.TEV_KCSEL_7_8
TEV_KCSEL_3_4 = ConstantColor.TEV_KCSEL_3_4
TEV_KCSEL_5_8 = ConstantColor.TEV_KCSEL_5_8
TEV_KCSEL_1_2 = ConstantColor.TEV_KCSEL_1_2
TEV_KCSEL_3_8 = ConstantColor.TEV_KCSEL_3_8
TEV_KCSEL_1_4 = ConstantColor.TEV_KCSEL_1_4
TEV_KCSEL_1_8 = ConstantColor.TEV_KCSEL_1_8
TEV_KCSEL_K0 = ConstantColor.TEV_KCSEL_K0
TEV_KCSEL_K1 = ConstantColor.TEV_KCSEL_K1
TEV_KCSEL_K2 = ConstantColor.TEV_KCSEL_K2
TEV_KCSEL_K3 = ConstantColor.TEV_KCSEL_K3
TEV_KCSEL_K0_R = ConstantColor.TEV_KCSEL_K0_R
TEV_KCSEL_K1_R = ConstantColor.TEV_KCSEL_K1_R
TEV_KCSEL_K2_R = ConstantColor.TEV_KCSEL_K2_R
TEV_KCSEL_K3_R = ConstantColor.TEV_KCSEL_K3_R
TEV_KCSEL_K0_G = ConstantColor.TEV_KCSEL_K0_G
TEV_KCSEL_K1_G = ConstantColor.TEV_KCSEL_K1_G
TEV_KCSEL_K2_G = ConstantColor.TEV_KCSEL_K2_G
TEV_KCSEL_K3_G = ConstantColor.TEV_KCSEL_K3_G
TEV_KCSEL_K0_B = ConstantColor.TEV_KCSEL_K0_B
TEV_KCSEL_K1_B = ConstantColor.TEV_KCSEL_K1_B
TEV_KCSEL_K2_B = ConstantColor.TEV_KCSEL_K2_B
TEV_KCSEL_K3_B = ConstantColor.TEV_KCSEL_K3_B
TEV_KCSEL_K0_A = ConstantColor.TEV_KCSEL_K0_A
TEV_KCSEL_K1_A = ConstantColor.TEV_KCSEL_K1_A
TEV_KCSEL_K2_A = ConstantColor.TEV_KCSEL_K2_A
TEV_KCSEL_K3_A = ConstantColor.TEV_KCSEL_K3_A


class ConstantAlpha(Enum):
    TEV_KASEL_1 = 0
    TEV_KASEL_7_8 = 1
    TEV_KASEL_3_4 = 2
    TEV_KASEL_5_8 = 3
    TEV_KASEL_1_2 = 4
    TEV_KASEL_3_8 = 5
    TEV_KASEL_1_4 = 6
    TEV_KASEL_1_8 = 7
    TEV_KASEL_K0_R = 16
    TEV_KASEL_K1_R = 17
    TEV_KASEL_K2_R = 18
    TEV_KASEL_K3_R = 19
    TEV_KASEL_K0_G = 20
    TEV_KASEL_K1_G = 21
    TEV_KASEL_K2_G = 22
    TEV_KASEL_K3_G = 23
    TEV_KASEL_K0_B = 24
    TEV_KASEL_K1_B = 25
    TEV_KASEL_K2_B = 26
    TEV_KASEL_K3_B = 27
    TEV_KASEL_K0_A = 28
    TEV_KASEL_K1_A = 29
    TEV_KASEL_K2_A = 30
    TEV_KASEL_K3_A = 31


TEV_KASEL_1 = ConstantAlpha.TEV_KASEL_1
TEV_KASEL_7_8 = ConstantAlpha.TEV_KASEL_7_8
TEV_KASEL_3_4 = ConstantAlpha.TEV_KASEL_3_4
TEV_KASEL_5_8 = ConstantAlpha.TEV_KASEL_5_8
TEV_KASEL_1_2 = ConstantAlpha.TEV_KASEL_1_2
TEV_KASEL_3_8 = ConstantAlpha.TEV_KASEL_3_8
TEV_KASEL_1_4 = ConstantAlpha.TEV_KASEL_1_4
TEV_KASEL_1_8 = ConstantAlpha.TEV_KASEL_1_8
TEV_KASEL_K0_R = ConstantAlpha.TEV_KASEL_K0_R
TEV_KASEL_K1_R = ConstantAlpha.TEV_KASEL_K1_R
TEV_KASEL_K2_R = ConstantAlpha.TEV_KASEL_K2_R
TEV_KASEL_K3_R = ConstantAlpha.TEV_KASEL_K3_R
TEV_KASEL_K0_G = ConstantAlpha.TEV_KASEL_K0_G
TEV_KASEL_K1_G = ConstantAlpha.TEV_KASEL_K1_G
TEV_KASEL_K2_G = ConstantAlpha.TEV_KASEL_K2_G
TEV_KASEL_K3_G = ConstantAlpha.TEV_KASEL_K3_G
TEV_KASEL_K0_B = ConstantAlpha.TEV_KASEL_K0_B
TEV_KASEL_K1_B = ConstantAlpha.TEV_KASEL_K1_B
TEV_KASEL_K2_B = ConstantAlpha.TEV_KASEL_K2_B
TEV_KASEL_K3_B = ConstantAlpha.TEV_KASEL_K3_B
TEV_KASEL_K0_A = ConstantAlpha.TEV_KASEL_K0_A
TEV_KASEL_K1_A = ConstantAlpha.TEV_KASEL_K1_A
TEV_KASEL_K2_A = ConstantAlpha.TEV_KASEL_K2_A
TEV_KASEL_K3_A = ConstantAlpha.TEV_KASEL_K3_A


class SwapTable(Enum):
    TEV_SWAP0 = Value(0,index=0)
    TEV_SWAP1 = Value(1,index=1)
    TEV_SWAP2 = Value(2,index=2)
    TEV_SWAP3 = Value(3,index=3)


TEV_SWAP0 = SwapTable.TEV_SWAP0
TEV_SWAP1 = SwapTable.TEV_SWAP1
TEV_SWAP2 = SwapTable.TEV_SWAP2
TEV_SWAP3 = SwapTable.TEV_SWAP3
TEV_SWAP = [TEV_SWAP0,TEV_SWAP1,TEV_SWAP2,TEV_SWAP3]


class ColorComponent(Enum):
    CH_RED = 0
    CH_GREEN = 1
    CH_BLUE = 2
    CH_ALPHA = 3


CH_RED = ColorComponent.CH_RED
CH_GREEN = ColorComponent.CH_GREEN
CH_BLUE = ColorComponent.CH_BLUE
CH_ALPHA = ColorComponent.CH_ALPHA


class IndirectStage(Enum):
    INDTEXSTAGE0 = Value(0,index=0)
    INDTEXSTAGE1 = Value(1,index=1)
    INDTEXSTAGE2 = Value(2,index=2)
    INDTEXSTAGE3 = Value(3,index=3)


INDTEXSTAGE0 = IndirectStage.INDTEXSTAGE0
INDTEXSTAGE1 = IndirectStage.INDTEXSTAGE1
INDTEXSTAGE2 = IndirectStage.INDTEXSTAGE2
INDTEXSTAGE3 = IndirectStage.INDTEXSTAGE3
INDTEXSTAGE = [INDTEXSTAGE0,INDTEXSTAGE1,INDTEXSTAGE2,INDTEXSTAGE3]


class IndirectFormat(Enum):
    ITF_8 = 0
    ITF_5 = 1
    ITF_4 = 2
    ITF_3 = 3


ITF_8 = IndirectFormat.ITF_8
ITF_5 = IndirectFormat.ITF_5
ITF_4 = IndirectFormat.ITF_4
ITF_3 = IndirectFormat.ITF_3


class IndirectBiasComponents(Enum):
    ITB_NONE = 0
    ITB_S = 1
    ITB_T = 2
    ITB_ST = 3
    ITB_U = 4
    ITB_SU = 5
    ITB_TU = 6
    ITB_STU = 7


ITB_NONE = IndirectBiasComponents.ITB_NONE
ITB_S = IndirectBiasComponents.ITB_S
ITB_T = IndirectBiasComponents.ITB_T
ITB_ST = IndirectBiasComponents.ITB_ST
ITB_U = IndirectBiasComponents.ITB_U
ITB_SU = IndirectBiasComponents.ITB_SU
ITB_TU = IndirectBiasComponents.ITB_TU
ITB_STU = IndirectBiasComponents.ITB_STU


class IndirectMatrix(Enum):
    ITM_OFF = 0
    ITM_0 = Value(1,index=0)
    ITM_1 = Value(2,index=1)
    ITM_2 = Value(3,index=2)
    ITM_S0 = Value(5,index=0)
    ITM_S1 = Value(6,index=1)
    ITM_S2 = Value(7,index=2)
    ITM_T0 = Value(9,index=0)
    ITM_T1 = Value(10,index=1)
    ITM_T2 = Value(11,index=2)


ITM_OFF = IndirectMatrix.ITM_OFF
ITM_0 = IndirectMatrix.ITM_0
ITM_1 = IndirectMatrix.ITM_1
ITM_2 = IndirectMatrix.ITM_2
ITM = [ITM_0,ITM_1,ITM_2]
ITM_S0 = IndirectMatrix.ITM_S0
ITM_S1 = IndirectMatrix.ITM_S1
ITM_S2 = IndirectMatrix.ITM_S2
ITM_S = [ITM_S0,ITM_S1,ITM_S2]
ITM_T0 = IndirectMatrix.ITM_T0
ITM_T1 = IndirectMatrix.ITM_T1
ITM_T2 = IndirectMatrix.ITM_T2
ITM_T = [ITM_T0,ITM_T1,ITM_T2]


class IndirectWrap(Enum):
    ITW_OFF = 0
    ITW_256 = 1
    ITW_128 = 2
    ITW_64 = 3
    ITW_32 = 4
    ITW_16 = 5
    ITW_0 = 6


ITW_OFF = IndirectWrap.ITW_OFF
ITW_256 = IndirectWrap.ITW_256
ITW_128 = IndirectWrap.ITW_128
ITW_64 = IndirectWrap.ITW_64
ITW_32 = IndirectWrap.ITW_32
ITW_16 = IndirectWrap.ITW_16
ITW_0 = IndirectWrap.ITW_0


class IndirectBumpAlpha(Enum):
    ITBA_OFF = 0
    ITBA_S = 1
    ITBA_T = 2
    ITBA_U = 3


ITBA_OFF = IndirectBumpAlpha.ITBA_OFF
ITBA_S = IndirectBumpAlpha.ITBA_S
ITBA_T = IndirectBumpAlpha.ITBA_T
ITBA_U = IndirectBumpAlpha.ITBA_U


class IndirectScale(Enum):
    ITS_1 = 0
    ITS_2 = 1
    ITS_4 = 2
    ITS_8 = 3
    ITS_16 = 4
    ITS_32 = 5
    ITS_64 = 6
    ITS_128 = 7
    ITS_256 = 8


ITS_1 = IndirectScale.ITS_1
ITS_2 = IndirectScale.ITS_2
ITS_4 = IndirectScale.ITS_4
ITS_8 = IndirectScale.ITS_8
ITS_16 = IndirectScale.ITS_16
ITS_32 = IndirectScale.ITS_32
ITS_64 = IndirectScale.ITS_64
ITS_128 = IndirectScale.ITS_128
ITS_256 = IndirectScale.ITS_256


class CullMode(Enum):
    CULL_NONE = 0
    CULL_FRONT = Value(1,gl_value=GL_FRONT)
    CULL_BACK = Value(2,gl_value=GL_BACK)
    CULL_ALL = Value(3,gl_value=GL_FRONT_AND_BACK)


CULL_NONE = CullMode.CULL_NONE
CULL_FRONT = CullMode.CULL_FRONT
CULL_BACK = CullMode.CULL_BACK
CULL_ALL = CullMode.CULL_ALL


class FogFunction(Enum):
    FOG_NONE = 0
    FOG_PERSP_LIN = 2
    FOG_PERSP_EXP = 4
    FOG_PERSP_EXP2 = 5
    FOG_PERSP_REVEXP = 6
    FOG_PERSP_REVEXP2 = 7
    FOG_ORTHO_LIN = 10
    FOG_ORTHO_EXP = 12
    FOG_ORTHO_EXP2 = 13
    FOG_ORTHO_REVEXP = 14
    FOG_ORTHO_REVEXP2 = 15
    FOG_LIN = FOG_PERSP_LIN
    FOG_EXP = FOG_PERSP_EXP
    FOG_EXP2 = FOG_PERSP_EXP2
    FOG_REVEXP = FOG_PERSP_REVEXP
    FOG_REVEXP2 = FOG_PERSP_REVEXP2


FOG_NONE = FogFunction.FOG_NONE
FOG_PERSP_LIN = FogFunction.FOG_PERSP_LIN
FOG_PERSP_EXP = FogFunction.FOG_PERSP_EXP
FOG_PERSP_EXP2 = FogFunction.FOG_PERSP_EXP2
FOG_PERSP_REVEXP = FogFunction.FOG_REVEXP
FOG_PERSP_REVEXP2 = FogFunction.FOG_REVEXP2
FOG_ORTHO_LIN = FogFunction.FOG_ORTHO_LIN
FOG_ORTHO_EXP = FogFunction.FOG_ORTHO_EXP
FOG_ORTHO_EXP2 = FogFunction.FOG_ORTHO_EXP2
FOG_ORTHO_REVEXP = FogFunction.FOG_ORTHO_REVEXP
FOG_ORTHO_REVEXP2 = FogFunction.FOG_ORTHO_REVEXP2
FOG_LIN = FogFunction.FOG_LIN
FOG_EXP = FogFunction.FOG_EXP
FOG_EXP2 = FogFunction.FOG_EXP2
FOG_REVEXP = FogFunction.FOG_REVEXP
FOG_REVEXP2 = FogFunction.FOG_REVEXP2


class AlphaOperator(Enum):
    AOP_AND = 0
    AOP_OR = 1
    AOP_XOR = 2
    AOP_XNOR = 3


AOP_AND = AlphaOperator.AOP_AND
AOP_OR = AlphaOperator.AOP_OR
AOP_XOR = AlphaOperator.AOP_XOR
AOP_XNOR = AlphaOperator.AOP_XNOR


class CompareFunction(Enum):
    NEVER = Value(0,gl_value=GL_NEVER)
    LESS = Value(1,gl_value=GL_LESS)
    EQUAL = Value(2,gl_value=GL_EQUAL)
    LEQUAL = Value(3,gl_value=GL_LEQUAL)
    GREATER = Value(4,gl_value=GL_GREATER)
    NEQUAL = Value(5,gl_value=GL_NOTEQUAL)
    GEQUAL = Value(6,gl_value=GL_GEQUAL)
    ALWAYS = Value(7,gl_value=GL_ALWAYS)


NEVER = CompareFunction.NEVER
LESS = CompareFunction.LESS
EQUAL = CompareFunction.EQUAL
LEQUAL = CompareFunction.LEQUAL
GREATER = CompareFunction.GREATER
NEQUAL = CompareFunction.NEQUAL
GEQUAL = CompareFunction.GEQUAL
ALWAYS = CompareFunction.ALWAYS


class BlendFunction(Enum):
    BM_NONE = 0
    BM_BLEND = 1
    BM_LOGIC = 2
    BM_SUBTRACT = 3


BM_NONE = BlendFunction.BM_NONE
BM_BLEND = BlendFunction.BM_BLEND
BM_LOGIC = BlendFunction.BM_LOGIC
BM_SUBTRACT = BlendFunction.BM_SUBTRACT


class BlendFactor(Enum):
    BL_ZERO = Value(0,gl_value=GL_ZERO)
    BL_ONE = Value(1,gl_value=GL_ONE)
    BL_SRCALPHA = Value(4,gl_value=GL_SRC_ALPHA)
    BL_INVSRCALPHA = Value(5,gl_value=GL_ONE_MINUS_SRC_ALPHA)
    BL_DSTALPHA = Value(6,gl_value=GL_DST_ALPHA)
    BL_INVDSTALPHA = Value(7,gl_value=GL_ONE_MINUS_DST_ALPHA)


class BlendSourceFactor(BlendFactor,metaclass=ExtendEnumMeta):
    BL_DSTCLR = Value(2,gl_value=GL_DST_COLOR)
    BL_INVDSTCLR = Value(3,gl_value=GL_ONE_MINUS_DST_COLOR)


class BlendDestinationFactor(BlendFactor,metaclass=ExtendEnumMeta):
    BL_SRCCLR = Value(2,gl_value=GL_SRC_COLOR)
    BL_INVSRCCLR = Value(3,gl_value=GL_ONE_MINUS_SRC_COLOR)


BL_ZERO = BlendFactor.BL_ZERO
BL_ONE = BlendFactor.BL_ONE
BL_SRCCLR = BlendDestinationFactor.BL_SRCCLR
BL_INVSRCCLR = BlendDestinationFactor.BL_INVSRCCLR
BL_DSTCLR = BlendSourceFactor.BL_DSTCLR
BL_INVDSTCLR = BlendSourceFactor.BL_INVDSTCLR
BL_SRCALPHA = BlendFactor.BL_SRCALPHA
BL_INVSRCALPHA = BlendFactor.BL_INVSRCALPHA
BL_DSTALPHA = BlendFactor.BL_DSTALPHA
BL_INVDSTALPHA = BlendFactor.BL_INVDSTALPHA


class LogicalOperation(Enum):
    LO_CLEAR = Value(0,gl_value=GL_CLEAR)
    LO_AND = Value(1,gl_value=GL_AND)
    LO_REVAND = Value(2,gl_value=GL_AND_REVERSE)
    LO_COPY = Value(3,gl_value=GL_COPY)
    LO_INVAND = Value(4,gl_value=GL_AND_INVERTED)
    LO_NOOP = Value(5,gl_value=GL_NOOP)
    LO_XOR = Value(6,gl_value=GL_XOR)
    LO_OR = Value(7,gl_value=GL_OR)
    LO_NOR = Value(8,gl_value=GL_NOR)
    LO_EQUIV = Value(9,gl_value=GL_EQUIV)
    LO_INV = Value(10,gl_value=GL_INVERT)
    LO_REVOR = Value(11,gl_value=GL_OR_INVERTED)
    LO_INVCOPY = Value(12,gl_value=GL_COPY_INVERTED)
    LO_INVOR = Value(13,gl_value=GL_OR_INVERTED)
    LO_INVNAND = Value(14,gl_value=GL_NAND)
    LO_SET = Value(15,gl_value=GL_SET)


LO_CLEAR = LogicalOperation.LO_CLEAR
LO_AND = LogicalOperation.LO_AND
LO_REVAND = LogicalOperation.LO_REVAND
LO_COPY = LogicalOperation.LO_COPY
LO_INVAND = LogicalOperation.LO_INVAND
LO_NOOP = LogicalOperation.LO_NOOP
LO_XOR = LogicalOperation.LO_XOR
LO_OR = LogicalOperation.LO_OR
LO_NOR = LogicalOperation.LO_NOR
LO_EQUIV = LogicalOperation.LO_EQUIV
LO_INV = LogicalOperation.LO_INV
LO_REVOR = LogicalOperation.LO_REVOR
LO_INVCOPY = LogicalOperation.LO_INVCOPY
LO_INVOR = LogicalOperation.LO_INVOR
LO_INVNAND = LogicalOperation.LO_INVAND
LO_SET = LogicalOperation.LO_SET


class Aniso(Enum):
    ANISO_1 = 0
    ANISO_2 = 1
    ANISO_3 = 2


ANISO_1 = Aniso.ANISO_1
ANISO_2 = Aniso.ANISO_2
ANISO_3 = Aniso.ANISO_3

