"""Module for reading and writing data structures."""

from btypes.types import *

class FormatError(Exception): pass

SEEK_POS = 0
SEEK_CUR = 1
SEEK_END = 2

cstring = CString('ascii')
pstring = PString('ascii')


def align(stream,length,padding=b'This is padding data to alignment.'):
    if stream.tell() % length == 0: return
    n,r = divmod(length - (stream.tell() % length),len(padding))
    stream.write(n*padding + padding[0:r])

