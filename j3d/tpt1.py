from btypes.big_endian import *
from j3d.animation import Animation,IncompatibleAnimationError
import j3d.string_table


class Header(Struct):
    magic = ByteString(4)
    section_size = uint32
    loop_mode = uint8
    __padding__ = Padding(1)
    duration = uint16
    material_animation_count = uint16
    texture_index_count = uint16
    texture_index_selection_offset = uint32
    texture_index_offset = uint32
    material_index_offset = uint32
    name_offset = uint32


class TextureIndexSelection(Struct):
    count = uint16
    first = uint16
    unknown0 = uint8
    __padding__ = Padding(3)


class MaterialAnimation: pass


class TextureSwapAnimation(Animation):

    def __init__(self,duration,loop_mode,material_animations):
        super().__init__(duration,loop_mode)
        self.material_animations = material_animations

    def attach(self,model):
        for material_animation in self.material_animations:
            if material_animation.material_index >= len(model.materials):
                raise IncompatibleAnimationError()
            if material_animation.name != model.materials[material_animation.material_index].name:
                raise IncompatibleAnimationError()
            if max(material_animation.texture_indices) >= len(model.textures):
                raise IncompatibleAnimationError()

        self.time = -1
        self.model = model

    def update_model(self):
        for material_animation in self.material_animations:
            if self.time >= len(material_animation.texture_indices):
                texture_index = material_animation.texture_indices[-1]
            else:
                texture_index = material_animation.texture_indices[self.time]
            self.model.materials[material_animation.material_index].gl_texture_indices[0] = texture_index


def unpack(stream):
    base = stream.tell()
    header = Header.unpack(stream)
    if header.magic != b'TPT1':
        raise FormatError('invalid magic')

    stream.seek(base + header.texture_index_selection_offset)
    texture_index_selections = [TextureIndexSelection.unpack(stream) for _ in range(header.material_animation_count)]

    stream.seek(base + header.texture_index_offset)
    texture_indices = [uint16.unpack(stream) for _ in range(header.texture_index_count)]

    stream.seek(base + header.material_index_offset)
    material_indices = [uint16.unpack(stream) for _ in range(header.material_animation_count)]

    stream.seek(base + header.name_offset)
    names = j3d.string_table.unpack(stream)

    material_animations = [MaterialAnimation() for _ in range(header.material_animation_count)]

    for material_animation,texture_index_selection,material_index,name in zip(material_animations,texture_index_selections,material_indices,names):
        material_animation.texture_indices = texture_indices[texture_index_selection.first:texture_index_selection.first + texture_index_selection.count]
        material_animation.material_index = material_index
        material_animation.name = name

    stream.seek(base + header.section_size)
    return TextureSwapAnimation(header.duration,header.loop_mode,material_animations)

