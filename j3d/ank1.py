from btypes.big_endian import *
from j3d.animation import Animation,select_interpolater,IncompatibleAnimationError


class Header(Struct):
    magic = ByteString(4)
    section_size = uint32
    loop_mode = uint8
    angle_scale_exponent = uint8
    duration = uint16
    joint_animation_count = uint16
    scale_count = uint16
    rotation_count = uint16
    translation_count = uint16
    joint_animation_offset = uint32
    scale_offset = uint32
    rotation_offset = uint32
    translation_offset = uint32


class Selection(Struct):
    count = uint16
    first = uint16
    unknown0 = uint16


class ComponentAnimation(Struct):
    scale_selection = Selection
    rotation_selection = Selection
    translation_selection = Selection


class JointAnimation(Struct):
    x = ComponentAnimation
    y = ComponentAnimation
    z = ComponentAnimation


class SkeletalAnimation(Animation):
    
    def __init__(self,duration,loop_mode,joint_animations):
        super().__init__(duration,loop_mode)
        self.joint_animations = joint_animations

    def attach(self,model):
        if len(self.joint_animations) != len(model.joints):
            raise IncompatibleAnimationError()
        self.time = -1
        self.model = model

    def update_model(self):
        for joint_animation,joint in zip(self.joint_animations,self.model.gl_joints):
            joint.scale_x = joint_animation.x.scale.interpolate(self.time)
            joint.rotation_x = joint_animation.x.rotation.interpolate(self.time)
            joint.translation_x = joint_animation.x.translation.interpolate(self.time)
            joint.scale_y = joint_animation.y.scale.interpolate(self.time)
            joint.rotation_y = joint_animation.y.rotation.interpolate(self.time)
            joint.translation_y = joint_animation.y.translation.interpolate(self.time)
            joint.scale_z = joint_animation.z.scale.interpolate(self.time)
            joint.rotation_z = joint_animation.z.rotation.interpolate(self.time)
            joint.translation_z = joint_animation.z.translation.interpolate(self.time)

        self.model.gl_update_matrix_table()


def unpack(stream):
    base = stream.tell()
    header = Header.unpack(stream)
    if header.magic != b'ANK1':
        raise FormatError('invalid magic')

    stream.seek(base + header.joint_animation_offset)
    joint_animations = [JointAnimation.unpack(stream) for _ in range(header.joint_animation_count)]

    stream.seek(base + header.scale_offset)
    scales = [float32.unpack(stream) for _ in range(header.scale_count)]

    stream.seek(base + header.rotation_offset)
    rotations = [sint16.unpack(stream) for _ in range(header.rotation_count)]

    stream.seek(base + header.translation_offset)
    translations = [float32.unpack(stream) for _ in range(header.translation_count)]

    angle_scale = 180/32767*2**header.angle_scale_exponent

    for joint_animation in joint_animations:
        joint_animation.x.scale = select_interpolater(joint_animation.x.scale_selection,scales)
        joint_animation.x.rotation = select_interpolater(joint_animation.x.rotation_selection,rotations,angle_scale)
        joint_animation.x.translation = select_interpolater(joint_animation.x.translation_selection,translations)
        joint_animation.y.scale = select_interpolater(joint_animation.y.scale_selection,scales)
        joint_animation.y.rotation = select_interpolater(joint_animation.y.rotation_selection,rotations,angle_scale)
        joint_animation.y.translation = select_interpolater(joint_animation.y.translation_selection,translations)
        joint_animation.z.scale = select_interpolater(joint_animation.z.scale_selection,scales)
        joint_animation.z.rotation = select_interpolater(joint_animation.z.rotation_selection,rotations,angle_scale)
        joint_animation.z.translation = select_interpolater(joint_animation.z.translation_selection,translations)

    stream.seek(base + header.section_size)
    return SkeletalAnimation(header.duration,header.loop_mode,joint_animations)

