from math import cos,sin,radians
import numpy
from btypes.big_endian import *
import gx
from j3d.animation import Animation,select_interpolater,IncompatibleAnimationError
import j3d.string_table


class Header(Struct):
    magic = ByteString(4)
    section_size = uint32
    loop_mode = uint8
    angle_scale_exponent = uint8
    duration = uint16
    component_animation_count = uint16
    scale_count = uint16
    rotation_count = uint16
    translation_count = uint16
    component_animation_offset = uint32
    index_offset = uint32
    name_offset = uint32
    texture_matrix_index_offset = uint32
    center_offset = uint32
    scale_offset = uint32
    rotation_offset = uint32
    translation_offset = uint32

    def __init__(self):
        self.magic = b'TTK1'


class Selection(Struct):
    count = uint16
    first = uint16
    unknown0 = uint16


class ComponentAnimation(Struct):
    scale_selection = Selection
    rotation_selection = Selection
    translation_selection = Selection


class MatrixAnimation:

    def attach(self,material):
        self.texture_matrix = material.gl_block['texture_matrix{}'.format(self.texture_matrix_index)]
        matrix = material.texture_matrices[self.texture_matrix_index]
        if matrix.shape == gx.TG_MTX2x4:
            self.row_count = 2
        elif matrix.shape == gx.TG_MTX3x4:
            self.row_count = 3
        else:
            raise ValueError('invalid texture matrix shape')

    def update(self,time):
        scale_x = self.scale_x.interpolate(time)
        scale_y = self.scale_y.interpolate(time)
        scale_z = self.scale_z.interpolate(time)
        rotation_x = self.rotation_x.interpolate(time)
        rotation_y = self.rotation_y.interpolate(time)
        rotation_z = self.rotation_z.interpolate(time)
        translation_x = self.translation_x.interpolate(time)
        translation_y = self.translation_y.interpolate(time)
        translation_z = self.translation_z.interpolate(time)

        cx = cos(radians(rotation_x))
        sx = sin(radians(rotation_x))
        cy = cos(radians(rotation_y))
        sy = sin(radians(rotation_y))
        cz = cos(radians(rotation_z))
        sz = sin(radians(rotation_z))

        R = numpy.matrix([[0,0,0,0],[0,0,0,0],[0,0,0,0],[0,0,0,1.0]]) #<-?
        R[0,0] = cy*cz
        R[0,1] = (sx*sy*cz - cx*sz)
        R[0,2] = (cx*sy*cz + sx*sz)
        R[1,0] = cy*sz
        R[1,1] = (sx*sy*sz + cx*cz)
        R[1,2] = (cx*sy*sz - sx*cz)
        R[2,0] = -sy
        R[2,1] = sx*cy
        R[2,2] = cx*cy

        S = numpy.matrix([[scale_x,0,0,0],[0,scale_y,0,0],[0,0,scale_z,0],[0,0,0,1]])
        C = numpy.matrix([[1,0,0,self.center_x],[0,1,0,self.center_y],[0,0,1,self.center_z],[0,0,0,1]])
        T = numpy.matrix([[1,0,0,translation_x],[0,1,0,translation_y],[0,0,1,translation_z],[0,0,0,1]])

        self.texture_matrix[:] = (T*C*S*R*C.I)[:self.row_count,:]


class TextureMatrixAnimation(Animation):
    
    def __init__(self,duration,loop_mode,texture_matrix_animations):
        super().__init__(duration,loop_mode)
        self.texture_matrix_animations = texture_matrix_animations

    def attach(self,model):
        for texture_matrix_animation in self.texture_matrix_animations:
            for material in model.materials:
                if material.name == texture_matrix_animation.material_name:
                    texture_matrix_animation.attach(material)
                    break
            else:
                raise IncompatibleAnimationError()

        self.time = -1

    def update_model(self):
        for texture_matrix_animation in self.texture_matrix_animations:
            texture_matrix_animation.update(self.time)


def unpack(stream):
    base = stream.tell()
    header = Header.unpack(stream)
    if header.magic != b'TTK1':
        raise FormatError('invalid magic')

    stream.seek(base + header.component_animation_offset)
    component_animations = [ComponentAnimation.unpack(stream) for _ in range(header.component_animation_count)]

    stream.seek(base + header.index_offset)
    for index in range(header.component_animation_count//3):
        if index != uint16.unpack(stream):
            raise FormatError('invalid index')

    stream.seek(base + header.name_offset)
    names = j3d.string_table.unpack(stream)

    stream.seek(base + header.texture_matrix_index_offset)
    texture_matrix_indices = [uint8.unpack(stream) for _ in range(header.component_animation_count//3)]

    stream.seek(base + header.center_offset)
    centers = [float32.unpack(stream) for _ in range(header.component_animation_count)]

    stream.seek(base + header.scale_offset)
    scales = [float32.unpack(stream) for _ in range(header.scale_count)]

    stream.seek(base + header.rotation_offset)
    rotations = [sint16.unpack(stream) for _ in range(header.rotation_count)]

    stream.seek(base + header.translation_offset)
    translations = [float32.unpack(stream) for _ in range(header.translation_count)]

    angle_scale = 180/32767*2**header.angle_scale_exponent

    for component_animation in component_animations:
        component_animation.scale = select_interpolater(component_animation.scale_selection,scales)
        component_animation.rotation = select_interpolater(component_animation.rotation_selection,rotations,angle_scale)
        component_animation.translation = select_interpolater(component_animation.translation_selection,translations)

    texture_matrix_animations = [MatrixAnimation() for _ in range(header.component_animation_count//3)]

    for i,texture_matrix_animation in enumerate(texture_matrix_animations):
        texture_matrix_animation.material_name = names[i]
        texture_matrix_animation.texture_matrix_index = texture_matrix_indices[i]
        texture_matrix_animation.center_x = centers[3*i]
        texture_matrix_animation.center_y = centers[3*i + 1]
        texture_matrix_animation.center_z = centers[3*i + 2]
        texture_matrix_animation.scale_x = component_animations[3*i].scale
        texture_matrix_animation.scale_y = component_animations[3*i + 1].scale
        texture_matrix_animation.scale_z = component_animations[3*i + 2].scale
        texture_matrix_animation.rotation_x = component_animations[3*i].rotation
        texture_matrix_animation.rotation_y = component_animations[3*i + 1].rotation
        texture_matrix_animation.rotation_z = component_animations[3*i + 2].rotation
        texture_matrix_animation.translation_x = component_animations[3*i].translation
        texture_matrix_animation.translation_y = component_animations[3*i + 1].translation
        texture_matrix_animation.translation_z = component_animations[3*i + 2].translation

    stream.seek(base + header.section_size)
    return TextureMatrixAnimation(header.duration,header.loop_mode,texture_matrix_animations)

