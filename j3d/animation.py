from btypes.big_endian import *

import logging
logger = logging.getLogger(__name__)

class IncompatibleAnimationError(Exception): pass


class Header(Struct):
    magic = ByteString(4)
    file_type = ByteString(4)
    file_size = uint32
    section_count = uint32
    unknown0 = ByteString(4)
    __padding__ = Padding(12)


class KeyFrame:

    def __init__(self,time,value,tangent_in,tangent_out=None):
        self.time = time
        self.value = value
        self.tangent_in = tangent_in
        self.tangent_out = tangent_out if tangent_out is not None else tangent_in


class ConstantInterpolater:

    def __init__(self,value):
        self.value = value

    def interpolate(self,time):
        return self.value

    
class CubicSplineInterpolater:

    def __init__(self,keys):
        self.keys = keys

    def interpolate(self,time):
        if self.keys[-1].time < time:
            return self.keys[-1].value

        i = 1
        while self.keys[i].time < time: i += 1

        t = (time - self.keys[i - 1].time)/(self.keys[i].time - self.keys[i - 1].time)
        a = 2*(self.keys[i - 1].value - self.keys[i].value) + self.keys[i - 1].tangent_out + self.keys[i].tangent_in
        b = -3*self.keys[i - 1].value + 3*self.keys[i].value - 2*self.keys[i - 1].tangent_out - self.keys[i].tangent_in
        c = self.keys[i - 1].tangent_out
        d = self.keys[i - 1].value
        return ((a*t + b)*t + c)*t + d


class Animation:
    
    def __init__(self,duration,loop_mode):
        self.duration = duration
        self.loop_mode = loop_mode

    def attach(self,model): #<-?
        self.time = -1

    @property
    def is_finished(self):
        return self.time == self.duration and self.loop_mode == 0

    def advance_frame(self):
        self.time += 1
        if self.time == self.duration and self.loop_mode == 2:
            self.time = 0
        self.update_model()


def select_interpolater(selection,array,scale=None):
    if selection.count == 1:
        interpolater = ConstantInterpolater(array[selection.first])
    elif selection.unknown0 == 0:
        interpolater =  CubicSplineInterpolater([KeyFrame(*array[selection.first + 3*i:selection.first + 3*i + 3]) for i in range(selection.count)])
    elif selection.unknown0 == 1:
        interpolater = CubicSplineInterpolater([KeyFrame(*array[selection.first + 4*i:selection.first + 4*i + 4]) for i in range(selection.count)])
    else:
        raise ValueError('invalid selection unknkown0')

    if scale is not None:
        if isinstance(interpolater,ConstantInterpolater):
            interpolater.value *= scale
        else:
            for key in interpolater.keys:
                key.value *= scale
                key.tangent_in *= scale
                key.tangent_out *= scale

    return interpolater


import j3d.vaf1
import j3d.ank1
import j3d.pak1
import j3d.trk1
import j3d.tpt1
import j3d.ttk1


def unpack(stream):
    header = Header.unpack(stream)
    if header.magic != b'J3D1':
        raise FormatError('invalid magic')
    if header.section_count != 1:
        raise FormatError('invalid section count')
    if header.unknown0 not in {b'\xFF\xFF\xFF\xFF',b'SVR1',b'SVR3'}:
        logger.warning('unknown0 different from default')

    if header.file_type == b'bva1':
        animation = j3d.vaf1.unpack(stream)
    elif header.file_type == b'bck1':
        animation = j3d.ank1.unpack(stream)
    elif header.file_type == b'bpk1':
        animation = j3d.pak1.unpack(stream)
    elif header.file_type == b'brk1':
        animation = j3d.trk1.unpack(stream)
    elif header.file_type == b'btp1':
        animation = j3d.tpt1.unpack(stream)
    elif header.file_type == b'btk1':
        animation = j3d.ttk1.unpack(stream)
    else:
        raise FormatError('invalid file type')

    animation.unknown0 = header.unknown0

    return animation

