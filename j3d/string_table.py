from btypes.big_endian import *

cstring_sjis = CString('shift-jis')


class Header(Struct):
    string_count = uint16
    __padding__ = Padding(2)


class Entry(Struct):
    string_hash = uint16
    string_offset = uint16


def unsigned_to_signed_byte(b):
    return b - 0x100 if b & 0x80 else b


def calculate_hash(string):
    h = 0
    for b in string:
        h = (h*3 + unsigned_to_signed_byte(b)) & 0xFFFF
    return h


def pack(stream,strings):
    strings = [string.encode('shift-jis') for string in strings]

    header = Header()
    header.string_count = len(strings)
    Header.pack(stream,header)

    offset = Header.sizeof() + Entry.sizeof()*len(strings)

    for string in strings:
        entry = Entry()
        entry.string_hash = calculate_hash(string)
        entry.string_offset = offset
        Entry.pack(stream,entry)
        offset += len(string) + 1

    for string in strings:
        stream.write(string)
        stream.write(b'\0')


def unpack(stream):
    base = stream.tell()
    header = Header.unpack(stream)
    entries = [Entry.unpack(stream) for _ in range(header.string_count)]
    strings = []
    for entry in entries:
        stream.seek(base + entry.string_offset)
        strings.append(cstring_sjis.unpack(stream))
    return strings

