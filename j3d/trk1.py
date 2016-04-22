from btypes.big_endian import *
from j3d.animation import Animation,select_interpolater,IncompatibleAnimationError
import j3d.string_table


class Header(Struct):
    magic = ByteString(4)
    section_size = uint32
    loop_mode = uint8
    __padding__ = Padding(1)
    duration = uint16
    register_color_animation_count = uint16
    constant_color_animation_count = uint16
    register_r_count = uint16
    register_g_count = uint16
    register_b_count = uint16
    register_a_count = uint16
    constant_r_count = uint16
    constant_g_count = uint16
    constant_b_count = uint16
    constant_a_count = uint16
    register_color_animation_offset = uint32
    constant_color_animation_offset = uint32
    register_index_offset = uint32
    constant_index_offset = uint32
    register_name_offset = uint32
    constant_name_offset = uint32
    register_r_offset = uint32
    register_g_offset = uint32
    register_b_offset = uint32
    register_a_offset = uint32
    constant_r_offset = uint32
    constant_g_offset = uint32
    constant_b_offset = uint32
    constant_a_offset = uint32


class Selection(Struct):
    count = uint16
    first = uint16
    unknown0 = uint16


class ColorAnimation(Struct):
    r = Selection
    g = Selection
    b = Selection
    a = Selection
    unknown0 = uint8
    __padding__ = Padding(3)

    def attach(self,color):
        self.color = color

    def update(self,time):
        self.color[0] = self.r.interpolate(time)/255
        self.color[1] = self.g.interpolate(time)/255
        self.color[2] = self.b.interpolate(time)/255
        self.color[3] = self.a.interpolate(time)/255


class TevColorAnimation(Animation):
    
    def __init__(self,duration,loop_mode,register_color_animations,constant_color_animations):
        super().__init__(duration,loop_mode)
        self.register_color_animations = register_color_animations
        self.constant_color_animations = constant_color_animations

    def attach(self,model):
        for color_animation in self.register_color_animations:
            for material in model.materials:
                if material.name == color_animation.name:
                    color_animation.attach(material.gl_block['tev_color{}'.format(color_animation.unknown0)])
                    break
            else:
                raise IncompatibleAnimationError()

        for color_animation in self.constant_color_animations:
            for material in model.materials:
                if material.name == color_animation.name:
                    color_animation.attach(material.gl_block['kcolor{}'.format(color_animation.unknown0)])
                    break
            else:
                raise IncompatibleAnimationError()

        self.time = -1

    def update_model(self):
        for color_animation in self.register_color_animations:
            color_animation.update(self.time)

        for color_animation in self.constant_color_animations:
            color_animation.update(self.time)


def unpack(stream):
    base = stream.tell()
    header = Header.unpack(stream)
    if header.magic != b'TRK1':
        raise FormatError('invalid magic')

    stream.seek(base + header.register_color_animation_offset)
    register_color_animations = [ColorAnimation.unpack(stream) for _ in range(header.register_color_animation_count)]

    stream.seek(base + header.constant_color_animation_offset)
    constant_color_animations = [ColorAnimation.unpack(stream) for _ in range(header.constant_color_animation_count)]

    stream.seek(base + header.register_r_offset)
    register_r = [sint16.unpack(stream) for _ in range(header.register_r_count)]

    stream.seek(base + header.register_g_offset)
    register_g = [sint16.unpack(stream) for _ in range(header.register_g_count)]

    stream.seek(base + header.register_b_offset)
    register_b = [sint16.unpack(stream) for _ in range(header.register_b_count)]

    stream.seek(base + header.register_a_offset)
    register_a = [sint16.unpack(stream) for _ in range(header.register_a_count)]

    stream.seek(base + header.constant_r_offset)
    constant_r = [sint16.unpack(stream) for _ in range(header.constant_r_count)]

    stream.seek(base + header.constant_g_offset)
    constant_g = [sint16.unpack(stream) for _ in range(header.constant_g_count)]

    stream.seek(base + header.constant_b_offset)
    constant_b = [sint16.unpack(stream) for _ in range(header.constant_b_count)]

    stream.seek(base + header.constant_a_offset)
    constant_a = [sint16.unpack(stream) for _ in range(header.constant_a_count)]

    stream.seek(base + header.register_index_offset)
    for index in range(header.register_color_animation_count):
        if index != uint16.unpack(stream):
            raise FormatError('invalid index')

    stream.seek(base + header.constant_index_offset)
    for index in range(header.constant_color_animation_count):
        if index != uint16.unpack(stream):
            raise FormatError('invalid index')

    stream.seek(base + header.register_name_offset)
    register_names = j3d.string_table.unpack(stream)

    stream.seek(base + header.constant_name_offset)
    constant_names = j3d.string_table.unpack(stream)

    for color_animation,name in zip(register_color_animations,register_names):
        color_animation.r = select_interpolater(color_animation.r,register_r)
        color_animation.g = select_interpolater(color_animation.g,register_g)
        color_animation.b = select_interpolater(color_animation.b,register_b)
        color_animation.a = select_interpolater(color_animation.a,register_a)
        color_animation.name = name

    for color_animation,name in zip(constant_color_animations,constant_names):
        color_animation.r = select_interpolater(color_animation.r,constant_r)
        color_animation.g = select_interpolater(color_animation.g,constant_g)
        color_animation.b = select_interpolater(color_animation.b,constant_b)
        color_animation.a = select_interpolater(color_animation.a,constant_a)
        color_animation.name = name

    stream.seek(base + header.section_size)
    return TevColorAnimation(header.duration,header.loop_mode,register_color_animations,constant_color_animations)

