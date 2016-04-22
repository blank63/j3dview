from math import cos,sin,radians
import numpy
from btypes.big_endian import *
import j3d.string_table

import logging
logger = logging.getLogger(__name__)


class Header(Struct):
    magic = ByteString(4)
    section_size = uint32
    joint_count = uint16
    __padding__ = Padding(2)
    joint_offset = uint32
    index_offset = uint32
    name_offset = uint32

    def __init__(self):
        self.magic = b'JNT1'

    @classmethod
    def unpack(cls,stream):
        header = super().unpack(stream)
        if header.magic != b'JNT1':
            raise FormatError('invalid magic')
        return header


def matrix3x4_multiply(a,b):
    c = numpy.empty((3,4),numpy.float32)
    c[:,0:3] = numpy.dot(a[:,0:3],b[:,0:3])
    c[:,3] = numpy.dot(a[:,0:3],b[:,3])
    c[:,3] += a[:,3]
    return c


class Joint(Struct):
    # 0 -> has direct material/shape descendant
    # 2 -> only referenced by other joints
    unknown0 = uint16
    ignore_parent_scale = bool8
    __padding__ = Padding(1)
    scale_x = float32
    scale_y = float32
    scale_z = float32
    rotation_x = FixedPointConverter(sint16,180/32767)
    rotation_y = FixedPointConverter(sint16,180/32767)
    rotation_z = FixedPointConverter(sint16,180/32767)
    __padding__ = Padding(2)
    translation_x = float32
    translation_y = float32
    translation_z = float32
    bounding_radius = float32
    min_x = float32
    min_y = float32
    min_z = float32
    max_x = float32
    max_y = float32
    max_z = float32

    def __init__(self):
        self.unknown0 = 0
        self.ignore_parent_scale = False
        self.scale_x = 1
        self.scale_y = 1
        self.scale_z = 1
        self.rotation_x = 0
        self.rotation_y = 0
        self.rotation_z = 0
        self.translation_x = 0
        self.translation_y = 0
        self.translation_z = 0

    @classmethod
    def unpack(cls,stream):
        joint = super().unpack(stream)
        if joint.unknown0 not in {0,1,2}:
            logger.warning('unknown0 different from default')
        return joint

    def create_matrix(self,parent_joint,parent_joint_matrix):
        # The calculation of the local matrix is an optimized version of
        # local_matrix = T*IPS*R*S if ignore_parent_scale else T*R*S
        # where S, R and T is the scale, rotation and translation matrix
        # respectively and IPS is the inverse parent scale matrix.

        cx = cos(radians(self.rotation_x))
        sx = sin(radians(self.rotation_x))
        cy = cos(radians(self.rotation_y))
        sy = sin(radians(self.rotation_y))
        cz = cos(radians(self.rotation_z))
        sz = sin(radians(self.rotation_z))

        if self.ignore_parent_scale:
            ips_x = 1/parent_joint.scale_x
            ips_y = 1/parent_joint.scale_y
            ips_z = 1/parent_joint.scale_z
        else:
            ips_x = 1
            ips_y = 1
            ips_z = 1

        local_matrix = numpy.empty((3,4),numpy.float32)
        local_matrix[0,0] = cy*cz*self.scale_x*ips_x
        local_matrix[1,0] = cy*sz*self.scale_x*ips_y
        local_matrix[2,0] = -sy*self.scale_x*ips_z
        local_matrix[0,1] = (sx*sy*cz - cx*sz)*self.scale_y*ips_x
        local_matrix[1,1] = (sx*sy*sz + cx*cz)*self.scale_y*ips_y
        local_matrix[2,1] = sx*cy*self.scale_y*ips_z
        local_matrix[0,2] = (cx*sy*cz + sx*sz)*self.scale_z*ips_x
        local_matrix[1,2] = (cx*sy*sz - sx*cz)*self.scale_z*ips_y
        local_matrix[2,2] = cx*cy*self.scale_z*ips_z
        local_matrix[0,3] = self.translation_x
        local_matrix[1,3] = self.translation_y
        local_matrix[2,3] = self.translation_z

        return matrix3x4_multiply(parent_joint_matrix,local_matrix)


def pack(stream,joints):
    base = stream.tell()
    header = Header()
    header.joint_count = len(joints)
    stream.write(b'\x00'*Header.sizeof())

    header.joint_offset = stream.tell() - base
    for joint in joints:
        Joint.pack(stream,joint)

    header.index_offset = stream.tell() - base
    for index in range(len(joints)):
        uint16.pack(stream,index)

    align(stream,4)
    header.name_offset = stream.tell() - base
    j3d.string_table.pack(stream,(joint.name for joint in joints))

    align(stream,0x20)
    header.section_size = stream.tell() - base
    stream.seek(base)
    Header.pack(stream,header)
    stream.seek(base + header.section_size)


def unpack(stream):
    base = stream.tell()
    header = Header.unpack(stream)

    stream.seek(base + header.joint_offset)
    joints = [Joint.unpack(stream) for _ in range(header.joint_count)]

    stream.seek(base + header.index_offset)
    for index in range(header.joint_count):
        if index != uint16.unpack(stream):
            raise FormatError('invalid index')

    stream.seek(base + header.name_offset)
    names = j3d.string_table.unpack(stream)
    for joint,name in zip(joints,names):
        joint.name = name

    stream.seek(base + header.section_size)
    return joints

