from btypes.big_endian import *
from j3d.animation import Animation,IncompatibleAnimationError


class Header(Struct):
    magic = ByteString(4)
    section_size = uint32
    loop_mode = uint8
    __padding__ = Padding(1)
    duration = uint16
    shape_animation_count = uint16
    show_count = uint16
    show_selection_offset = uint32
    show_offset = uint32


class ShowSelection(Struct):
    count = uint16
    first = uint16


class ShapeAnimation: pass


class ShapeVisibilityAnimation(Animation):

    def __init__(self,duration,loop_mode,shape_animations):
        super().__init__(duration,loop_mode)
        self.shape_animations = shape_animations

    def attach(self,model):
        if len(self.shape_animations) != len(model.shapes):
            raise IncompatibleAnimationError()
        self.time = -1
        self.model = model

    def update_model(self):
        for shape,shape_animation in zip(self.model.shapes,self.shape_animations):
            if self.time >= len(shape_animation.shows):
                show = shape_animation.shows[-1]
            else:
                show = shape_animation.shows[self.time]
            shape.hide = not show


def unpack(stream):
    base = stream.tell()
    header = Header.unpack(stream)
    if header.magic != b'VAF1':
        raise FormatError('invalid magic')

    stream.seek(base + header.show_selection_offset)
    show_selections = [ShowSelection.unpack(stream) for _ in range(header.shape_animation_count)]

    stream.seek(base + header.show_offset)
    shows = [bool8.unpack(stream) for _ in range(header.show_count)]

    shape_animations = [ShapeAnimation() for _ in range(header.shape_animation_count)]

    for shape_animation,show_selection in zip(shape_animations,show_selections):
        shape_animation.shows = shows[show_selection.first:show_selection.first + show_selection.count]

    stream.seek(base + header.section_size)
    return ShapeVisibilityAnimation(header.duration,header.loop_mode,shape_animations)

