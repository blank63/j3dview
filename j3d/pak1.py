from btypes.big_endian import *
from j3d.animation import Animation,select_interpolater,IncompatibleAnimationError
import j3d.string_table


class Header(Struct):
    magic = ByteString(4)
    section_size = uint32
    loop_mode = uint8
    __padding__ = Padding(3)
    duration = uint16
    material_animation_count = uint16
    r_count = uint16
    g_count = uint16
    b_count = uint16
    a_count = uint16
    material_animation_offset = uint32
    index_offset = uint32
    name_offset = uint32
    r_offset = uint32
    g_offset = uint32
    b_offset = uint32
    a_offset = uint32


class Selection(Struct):
    count = uint16
    first = uint16
    unknown0 = uint16


class MaterialAnimation(Struct):
    r = Selection
    g = Selection
    b = Selection
    a = Selection

    def attach(self,material):
        self.material_color = material.gl_block['material_color0']

    def update(self,time):
        self.material_color[0] = self.r.interpolate(time)/255
        self.material_color[1] = self.g.interpolate(time)/255
        self.material_color[2] = self.b.interpolate(time)/255
        self.material_color[3] = self.a.interpolate(time)/255


class MaterialColorAnimation(Animation):
    
    def __init__(self,duration,loop_mode,material_animations):
        super().__init__(duration,loop_mode)
        self.material_animations = material_animations

    def attach(self,model):
        for material_animation in self.material_animations:
            for material in model.materials:
                if material.name == material_animation.name:
                    material_animation.attach(material)
                    break
            else:
                raise IncompatibleAnimationError()

        self.time = -1

    def update_model(self):
        for material_animation in self.material_animations:
            material_animation.update(self.time)


def unpack(stream):
    base = stream.tell()
    header = Header.unpack(stream)
    if header.magic != b'PAK1':
        raise FormatError('invalid magic')

    stream.seek(base + header.material_animation_offset)
    material_animations = [MaterialAnimation.unpack(stream) for _ in range(header.material_animation_count)]

    stream.seek(base + header.r_offset)
    r = [sint16.unpack(stream) for _ in range(header.r_count)]

    stream.seek(base + header.g_offset)
    g = [sint16.unpack(stream) for _ in range(header.g_count)]

    stream.seek(base + header.b_offset)
    b = [sint16.unpack(stream) for _ in range(header.b_count)]

    stream.seek(base + header.a_offset)
    a = [sint16.unpack(stream) for _ in range(header.a_count)]

    stream.seek(base + header.index_offset)
    for index in range(header.material_animation_count):
        if index != uint16.unpack(stream):
            raise FormatError('invalid index')

    stream.seek(base + header.name_offset)
    names = j3d.string_table.unpack(stream)

    for material_animation,name in zip(material_animations,names):
        material_animation.r = select_interpolater(material_animation.r,r)
        material_animation.g = select_interpolater(material_animation.g,g)
        material_animation.b = select_interpolater(material_animation.b,b)
        material_animation.a = select_interpolater(material_animation.a,a)
        material_animation.name = name

    stream.seek(base + header.section_size)
    return MaterialColorAnimation(header.duration,header.loop_mode,material_animations)

