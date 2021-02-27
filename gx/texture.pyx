#cython: language_level=3, boundscheck=False, wraparound=False, cdivision=True, initializedcheck=False

"""Module for managing GameCube/Wii textures."""

import numpy
cimport numpy
import gx


# Conversion table: 3 bit to 8 bit
cdef numpy.uint8_t* cc38 = [
    0x00,0x24,0x49,0x6D, 0x92,0xB6,0xDB,0xFF
]

# Conversion table: 4 bit to 8 bit
cdef numpy.uint8_t* cc48 = [
    0x00,0x11,0x22,0x33, 0x44,0x55,0x66,0x77, 0x88,0x99,0xAA,0xBB, 0xCC,0xDD,0xEE,0xFF
]

# Conversion table: 5 bit to 8 bit
cdef numpy.uint8_t* cc58 = [
    0x00,0x08,0x10,0x18, 0x21,0x29,0x31,0x39, 0x42,0x4A,0x52,0x5A, 0x63,0x6B,0x73,0x7B,
    0x84,0x8C,0x94,0x9C, 0xA5,0xAD,0xB5,0xBD, 0xC6,0xCE,0xD6,0xDE, 0xE7,0xEF,0xF7,0xFF
]

# Conversion table: 6 bit to 8 bit
cdef numpy.uint8_t* cc68 = [
    0x00,0x04,0x08,0x0C, 0x10,0x14,0x18,0x1C, 0x20,0x24,0x28,0x2C, 0x30,0x34,0x38,0x3C,
    0x41,0x45,0x49,0x4D, 0x51,0x55,0x59,0x5D, 0x61,0x65,0x69,0x6D, 0x71,0x75,0x79,0x7D,
    0x82,0x86,0x8A,0x8E, 0x92,0x96,0x9A,0x9E, 0xA2,0xA6,0xAA,0xAE, 0xB2,0xB6,0xBA,0xBE,
    0xC3,0xC7,0xCB,0xCF, 0xD3,0xD7,0xDB,0xDF, 0xE3,0xE7,0xEB,0xEF, 0xF3,0xF7,0xFB,0xFF
]

# Conversion table: 8 bit to 3 bit
cdef numpy.uint8_t* cc83 = [
    0x00,0x00,0x00,0x00, 0x00,0x00,0x00,0x00, 0x00,0x00,0x00,0x00, 0x00,0x00,0x00,0x00,
    0x00,0x00,0x00,0x01, 0x01,0x01,0x01,0x01, 0x01,0x01,0x01,0x01, 0x01,0x01,0x01,0x01,
    0x01,0x01,0x01,0x01, 0x01,0x01,0x01,0x01, 0x01,0x01,0x01,0x01, 0x01,0x01,0x01,0x01,
    0x01,0x01,0x01,0x01, 0x01,0x01,0x01,0x02, 0x02,0x02,0x02,0x02, 0x02,0x02,0x02,0x02,
    0x02,0x02,0x02,0x02, 0x02,0x02,0x02,0x02, 0x02,0x02,0x02,0x02, 0x02,0x02,0x02,0x02,
    0x02,0x02,0x02,0x02, 0x02,0x02,0x02,0x02, 0x02,0x02,0x02,0x02, 0x03,0x03,0x03,0x03,
    0x03,0x03,0x03,0x03, 0x03,0x03,0x03,0x03, 0x03,0x03,0x03,0x03, 0x03,0x03,0x03,0x03,
    0x03,0x03,0x03,0x03, 0x03,0x03,0x03,0x03, 0x03,0x03,0x03,0x03, 0x03,0x03,0x03,0x03,
    0x04,0x04,0x04,0x04, 0x04,0x04,0x04,0x04, 0x04,0x04,0x04,0x04, 0x04,0x04,0x04,0x04,
    0x04,0x04,0x04,0x04, 0x04,0x04,0x04,0x04, 0x04,0x04,0x04,0x04, 0x04,0x04,0x04,0x04,
    0x04,0x04,0x04,0x04, 0x05,0x05,0x05,0x05, 0x05,0x05,0x05,0x05, 0x05,0x05,0x05,0x05,
    0x05,0x05,0x05,0x05, 0x05,0x05,0x05,0x05, 0x05,0x05,0x05,0x05, 0x05,0x05,0x05,0x05,
    0x05,0x05,0x05,0x05, 0x05,0x05,0x05,0x05, 0x05,0x06,0x06,0x06, 0x06,0x06,0x06,0x06,
    0x06,0x06,0x06,0x06, 0x06,0x06,0x06,0x06, 0x06,0x06,0x06,0x06, 0x06,0x06,0x06,0x06,
    0x06,0x06,0x06,0x06, 0x06,0x06,0x06,0x06, 0x06,0x06,0x06,0x06, 0x06,0x07,0x07,0x07,
    0x07,0x07,0x07,0x07, 0x07,0x07,0x07,0x07, 0x07,0x07,0x07,0x07, 0x07,0x07,0x07,0x07
]

# Conversion table: 8 bit to 4 bit
cdef numpy.uint8_t* cc84 = [
    0x00,0x00,0x00,0x00, 0x00,0x00,0x00,0x00, 0x00,0x01,0x01,0x01, 0x01,0x01,0x01,0x01,
    0x01,0x01,0x01,0x01, 0x01,0x01,0x01,0x01, 0x01,0x01,0x02,0x02, 0x02,0x02,0x02,0x02,
    0x02,0x02,0x02,0x02, 0x02,0x02,0x02,0x02, 0x02,0x02,0x02,0x03, 0x03,0x03,0x03,0x03,
    0x03,0x03,0x03,0x03, 0x03,0x03,0x03,0x03, 0x03,0x03,0x03,0x03, 0x04,0x04,0x04,0x04,
    0x04,0x04,0x04,0x04, 0x04,0x04,0x04,0x04, 0x04,0x04,0x04,0x04, 0x04,0x05,0x05,0x05,
    0x05,0x05,0x05,0x05, 0x05,0x05,0x05,0x05, 0x05,0x05,0x05,0x05, 0x05,0x05,0x06,0x06,
    0x06,0x06,0x06,0x06, 0x06,0x06,0x06,0x06, 0x06,0x06,0x06,0x06, 0x06,0x06,0x06,0x07,
    0x07,0x07,0x07,0x07, 0x07,0x07,0x07,0x07, 0x07,0x07,0x07,0x07, 0x07,0x07,0x07,0x07,
    0x08,0x08,0x08,0x08, 0x08,0x08,0x08,0x08, 0x08,0x08,0x08,0x08, 0x08,0x08,0x08,0x08,
    0x08,0x09,0x09,0x09, 0x09,0x09,0x09,0x09, 0x09,0x09,0x09,0x09, 0x09,0x09,0x09,0x09,
    0x09,0x09,0x0A,0x0A, 0x0A,0x0A,0x0A,0x0A, 0x0A,0x0A,0x0A,0x0A, 0x0A,0x0A,0x0A,0x0A,
    0x0A,0x0A,0x0A,0x0B, 0x0B,0x0B,0x0B,0x0B, 0x0B,0x0B,0x0B,0x0B, 0x0B,0x0B,0x0B,0x0B,
    0x0B,0x0B,0x0B,0x0B, 0x0C,0x0C,0x0C,0x0C, 0x0C,0x0C,0x0C,0x0C, 0x0C,0x0C,0x0C,0x0C,
    0x0C,0x0C,0x0C,0x0C, 0x0C,0x0D,0x0D,0x0D, 0x0D,0x0D,0x0D,0x0D, 0x0D,0x0D,0x0D,0x0D,
    0x0D,0x0D,0x0D,0x0D, 0x0D,0x0D,0x0E,0x0E, 0x0E,0x0E,0x0E,0x0E, 0x0E,0x0E,0x0E,0x0E,
    0x0E,0x0E,0x0E,0x0E, 0x0E,0x0E,0x0E,0x0F, 0x0F,0x0F,0x0F,0x0F, 0x0F,0x0F,0x0F,0x0F
]

# Conversion table: 8 bit to 5 bit
cdef numpy.uint8_t* cc85 = [
    0x00,0x00,0x00,0x00, 0x00,0x01,0x01,0x01, 0x01,0x01,0x01,0x01, 0x01,0x02,0x02,0x02,
    0x02,0x02,0x02,0x02, 0x02,0x03,0x03,0x03, 0x03,0x03,0x03,0x03, 0x03,0x04,0x04,0x04,
    0x04,0x04,0x04,0x04, 0x04,0x04,0x05,0x05, 0x05,0x05,0x05,0x05, 0x05,0x05,0x06,0x06,
    0x06,0x06,0x06,0x06, 0x06,0x06,0x07,0x07, 0x07,0x07,0x07,0x07, 0x07,0x07,0x08,0x08,
    0x08,0x08,0x08,0x08, 0x08,0x08,0x08,0x09, 0x09,0x09,0x09,0x09, 0x09,0x09,0x09,0x0A,
    0x0A,0x0A,0x0A,0x0A, 0x0A,0x0A,0x0A,0x0B, 0x0B,0x0B,0x0B,0x0B, 0x0B,0x0B,0x0B,0x0C,
    0x0C,0x0C,0x0C,0x0C, 0x0C,0x0C,0x0C,0x0C, 0x0D,0x0D,0x0D,0x0D, 0x0D,0x0D,0x0D,0x0D,
    0x0E,0x0E,0x0E,0x0E, 0x0E,0x0E,0x0E,0x0E, 0x0F,0x0F,0x0F,0x0F, 0x0F,0x0F,0x0F,0x0F,
    0x10,0x10,0x10,0x10, 0x10,0x10,0x10,0x10, 0x11,0x11,0x11,0x11, 0x11,0x11,0x11,0x11,
    0x12,0x12,0x12,0x12, 0x12,0x12,0x12,0x12, 0x13,0x13,0x13,0x13, 0x13,0x13,0x13,0x13,
    0x13,0x14,0x14,0x14, 0x14,0x14,0x14,0x14, 0x14,0x15,0x15,0x15, 0x15,0x15,0x15,0x15,
    0x15,0x16,0x16,0x16, 0x16,0x16,0x16,0x16, 0x16,0x17,0x17,0x17, 0x17,0x17,0x17,0x17,
    0x17,0x17,0x18,0x18, 0x18,0x18,0x18,0x18, 0x18,0x18,0x19,0x19, 0x19,0x19,0x19,0x19,
    0x19,0x19,0x1A,0x1A, 0x1A,0x1A,0x1A,0x1A, 0x1A,0x1A,0x1B,0x1B, 0x1B,0x1B,0x1B,0x1B,
    0x1B,0x1B,0x1B,0x1C, 0x1C,0x1C,0x1C,0x1C, 0x1C,0x1C,0x1C,0x1D, 0x1D,0x1D,0x1D,0x1D,
    0x1D,0x1D,0x1D,0x1E, 0x1E,0x1E,0x1E,0x1E, 0x1E,0x1E,0x1E,0x1F, 0x1F,0x1F,0x1F,0x1F
]

# Conversion table: 8 bit to 6 bit
cdef numpy.uint8_t* cc86 = [
    0x00,0x00,0x00,0x01, 0x01,0x01,0x01,0x02, 0x02,0x02,0x02,0x03, 0x03,0x03,0x03,0x04,
    0x04,0x04,0x04,0x05, 0x05,0x05,0x05,0x06, 0x06,0x06,0x06,0x07, 0x07,0x07,0x07,0x08,
    0x08,0x08,0x08,0x09, 0x09,0x09,0x09,0x0A, 0x0A,0x0A,0x0A,0x0B, 0x0B,0x0B,0x0B,0x0C,
    0x0C,0x0C,0x0C,0x0D, 0x0D,0x0D,0x0D,0x0E, 0x0E,0x0E,0x0E,0x0F, 0x0F,0x0F,0x0F,0x10,
    0x10,0x10,0x10,0x10, 0x11,0x11,0x11,0x11, 0x12,0x12,0x12,0x12, 0x13,0x13,0x13,0x13,
    0x14,0x14,0x14,0x14, 0x15,0x15,0x15,0x15, 0x16,0x16,0x16,0x16, 0x17,0x17,0x17,0x17,
    0x18,0x18,0x18,0x18, 0x19,0x19,0x19,0x19, 0x1A,0x1A,0x1A,0x1A, 0x1B,0x1B,0x1B,0x1B,
    0x1C,0x1C,0x1C,0x1C, 0x1D,0x1D,0x1D,0x1D, 0x1E,0x1E,0x1E,0x1E, 0x1F,0x1F,0x1F,0x1F,
    0x20,0x20,0x20,0x20, 0x21,0x21,0x21,0x21, 0x22,0x22,0x22,0x22, 0x23,0x23,0x23,0x23,
    0x24,0x24,0x24,0x24, 0x25,0x25,0x25,0x25, 0x26,0x26,0x26,0x26, 0x27,0x27,0x27,0x27,
    0x28,0x28,0x28,0x28, 0x29,0x29,0x29,0x29, 0x2A,0x2A,0x2A,0x2A, 0x2B,0x2B,0x2B,0x2B,
    0x2C,0x2C,0x2C,0x2C, 0x2D,0x2D,0x2D,0x2D, 0x2E,0x2E,0x2E,0x2E, 0x2F,0x2F,0x2F,0x2F,
    0x2F,0x30,0x30,0x30, 0x30,0x31,0x31,0x31, 0x31,0x32,0x32,0x32, 0x32,0x33,0x33,0x33,
    0x33,0x34,0x34,0x34, 0x34,0x35,0x35,0x35, 0x35,0x36,0x36,0x36, 0x36,0x37,0x37,0x37,
    0x37,0x38,0x38,0x38, 0x38,0x39,0x39,0x39, 0x39,0x3A,0x3A,0x3A, 0x3A,0x3B,0x3B,0x3B,
    0x3B,0x3C,0x3C,0x3C, 0x3C,0x3D,0x3D,0x3D, 0x3D,0x3E,0x3E,0x3E, 0x3E,0x3F,0x3F,0x3F
]


dxt1_block = numpy.dtype([
    ('color0', numpy.uint16),
    ('color1', numpy.uint16),
    ('indices', numpy.uint32)
])


cdef packed struct dxt1_block_t:
    numpy.uint16_t color0
    numpy.uint16_t color1
    numpy.uint32_t indices


def reinterpret_native_endian(array):
    return array.newbyteorder('=')


def reinterpret_elements(array, element_type, base_dimension):
    return array.view(element_type).reshape((array.shape[:base_dimension] + (-1,)))


cdef numpy.uint16_t swap_bytes_uint16(numpy.uint16_t source):
    return (source << 8) | (source >> 8)


cdef numpy.uint32_t swap_bytes_uint32(numpy.uint32_t source):
    return (source << 24) | ((source << 8) & 0xFF0000) | ((source >> 8) & 0xFF00) | (source >> 24)


cdef dxt1_block_t swap_bytes_dxt1_block(dxt1_block_t source):
    cdef dxt1_block_t destination
    destination.color0 = swap_bytes_uint16(source.color0)
    destination.color1 = swap_bytes_uint16(source.color1)
    destination.indices = swap_bytes_uint32(source.indices)
    return destination


cdef void swap_ia8(numpy.uint8_t[:] source, numpy.uint8_t[:] destination):
    # The components of the GX IA8 formats are stored alpha first, intensity last
    destination[1] = source[0]
    destination[0] = source[1]


cdef void rgb565_to_rgba8(numpy.uint16_t source, numpy.uint8_t[:] destination):
    destination[0] = cc58[(source >> 11) & 0x1F]
    destination[1] = cc68[(source >> 5) & 0x3F]
    destination[2] = cc58[source & 0x1F]
    destination[3] = 0xFF


cdef numpy.uint16_t rgba8_to_rgb565(numpy.uint8_t[:] source):
    return (cc85[source[0]] << 11) | (cc86[source[1]] << 5) | cc85[source[2]]


cdef void rgb5a3_to_rgba8(numpy.uint16_t source, numpy.uint8_t[:] destination):
    if source & 0x8000:
        destination[0] = cc58[(source >> 10) & 0x1F]
        destination[1] = cc58[(source >> 5) & 0x1F]
        destination[2] = cc58[source & 0x1F]
        destination[3] = 0xFF
    else:
        destination[0] = cc48[(source >> 8) & 0xF]
        destination[1] = cc48[(source >> 4) & 0xF]
        destination[2] = cc48[source & 0xF]
        destination[3] = cc38[(source >> 12) & 0x7]


cdef numpy.uint16_t rgba8_to_rgb5a3(numpy.uint8_t[:] source):
    cdef unsigned int a3 = cc83[source[3]]
    if a3 >= 0x7:
        return 0x8000 | (cc85[source[0]] << 10) | (cc85[source[1]] << 5) | cc85[source[2]]
    else:
        return (cc84[source[0]] << 8) | (cc84[source[1]] << 4) | cc84[source[2]] | (a3 << 12)


cdef void dxt1_decompress_block(dxt1_block_t source, numpy.uint8_t[:,:,:] destination):
    cdef numpy.uint8_t color_table[4][4]
    cdef unsigned int i, j, index

    rgb565_to_rgba8(source.color0, color_table[0])
    rgb565_to_rgba8(source.color1, color_table[1])

    if source.color0 > source.color1:
        color_table[2][0] = (2*color_table[0][0] + color_table[1][0])//3
        color_table[2][1] = (2*color_table[0][1] + color_table[1][1])//3
        color_table[2][2] = (2*color_table[0][2] + color_table[1][2])//3
        color_table[2][3] = 0xFF
        color_table[3][0] = (2*color_table[1][0] + color_table[0][0])//3
        color_table[3][1] = (2*color_table[1][1] + color_table[0][1])//3
        color_table[3][2] = (2*color_table[1][2] + color_table[0][2])//3
        color_table[3][3] = 0xFF
    else:
        color_table[2][0] = (color_table[0][0] + color_table[1][0])//2
        color_table[2][1] = (color_table[0][1] + color_table[1][1])//2
        color_table[2][2] = (color_table[0][2] + color_table[1][2])//2
        color_table[2][3] = 0xFF
        color_table[3][0] = (2*color_table[1][0] + color_table[0][0])//3
        color_table[3][1] = (2*color_table[1][1] + color_table[0][1])//3
        color_table[3][2] = (2*color_table[1][2] + color_table[0][2])//3
        color_table[3][3] = 0

    for i in range(destination.shape[0]):
        for j in range(destination.shape[1]):
            index = (source.indices >> (30 - 2*(4*i + j))) & 0x3
            destination[i,j,0] = color_table[index][0]
            destination[i,j,1] = color_table[index][1]
            destination[i,j,2] = color_table[index][2]
            destination[i,j,3] = color_table[index][3]


class PaletteBase(numpy.ndarray):

    def __init__(self, length):
        #TODO: Does the length have to be a power of 2 or a multiple of 32 or something?
        super().__init__(length, self.entry_type)


class PaletteIA8(PaletteBase):
    palette_format = gx.TL_IA8
    entry_type = numpy.dtype((numpy.uint8, 2))

    def decode_to_ia8(self, destination_palette=None):
        if destination_palette is None:
            destination_palette = numpy.empty((len(self), 2), numpy.uint8)

        cdef numpy.uint8_t[:,:] source = self
        cdef numpy.uint8_t[:,:] destination = destination_palette
        cdef unsigned int length = destination.shape[0]
        cdef unsigned int i

        for i in range(length):
            swap_ia8(source[i], destination[i])

        return destination_palette

    @classmethod
    def encode_from_ia8(cls, source_palette, destination_palette=None):
        if destination_palette is None:
            destination_palette = cls(len(source_palette))

        cdef numpy.uint8_t[:,:] source = source_palette
        cdef numpy.uint8_t[:,:] destination = destination_palette
        cdef unsigned int length = source.shape[0]
        cdef unsigned int i

        for i in range(length):
            swap_ia8(source[i], destination[i])

        return destination_palette


class PaletteRGB565(PaletteBase):
    palette_format = gx.TL_RGB565
    entry_type = numpy.dtype(numpy.uint16).newbyteorder('>')

    def decode_to_rgb565(self, destination_palette=None):
        if destination_palette is None:
            destination_palette = numpy.empty(len(self), numpy.uint16)

        cdef numpy.uint16_t[:] source = reinterpret_native_endian(self)
        cdef numpy.uint16_t[:] destination = destination_palette
        cdef unsigned int length = destination.shape[0]
        cdef unsigned int i

        for i in range(length):
            destination[i] = swap_bytes_uint16(source[i])

        return destination_palette

    @classmethod
    def encode_from_rgb565(cls, source_palette, destination_palette=None):
        if destination_palette is None:
            destination_palette = cls(len(source_palette))

        cdef numpy.uint16_t[:] source = source_palette
        cdef numpy.uint16_t[:] destination = reinterpret_native_endian(destination_palette)
        cdef unsigned int length = source.shape[0]
        cdef unsigned int i

        for i in range(length):
            destination[i] = swap_bytes_uint16(source[i])

        return destination_palette

    def decode_to_rgba8(self, destination_palette=None):
        if destination_palette is None:
            destination_palette = numpy.empty((len(self), 4), numpy.uint8)

        cdef numpy.uint16_t[:] source = reinterpret_native_endian(self)
        cdef numpy.uint8_t[:,:] destination = destination_palette
        cdef unsigned int length = destination.shape[0]
        cdef unsigned int i

        for i in range(length):
            rgb565_to_rgba8(swap_bytes_uint16(source[i]), destination[i])

        return destination_palette

    @classmethod
    def encode_from_rgba8(cls, source_palette, destination_palette=None):
        if destination_palette is None:
            destination_palette = cls(len(source_palette))

        cdef numpy.uint8_t[:,:] source = source_palette
        cdef numpy.uint16_t [:] destination = reinterpret_native_endian(destination_palette)
        cdef unsigned int length = source.shape[0]
        cdef unsigned int i

        for i in range(length):
            destination[i] = swap_bytes_uint16(rgba8_to_rgb565(source[i]))

        return destination_palette


class PaletteRGB5A3(PaletteBase):
    palette_format = gx.TL_RGB5A3
    entry_type = numpy.dtype(numpy.uint16).newbyteorder('>')

    def decode_to_rgba8(self, destination_palette=None):
        if destination_palette is None:
            destination_palette = numpy.empty((len(self), 4), numpy.uint8)

        cdef numpy.uint16_t[:] source = reinterpret_native_endian(self)
        cdef numpy.uint8_t[:,:] destination = destination_palette
        cdef unsigned int length = destination.shape[0]
        cdef unsigned int i

        for i in range(length):
            rgb5a3_to_rgba8(swap_bytes_uint16(source[i]), destination[i])

        return destination_palette

    @classmethod
    def encode_from_rgba8(cls, source_palette, destination_palette=None):
        if destination_palette is None:
            destination_palette = cls(len(source_palette))

        cdef numpy.uint8_t[:,:] source = source_palette
        cdef numpy.uint16_t[:] destination = reinterpret_native_endian(destination_palette)
        cdef unsigned int length = source.shape[0]
        cdef unsigned int i

        for i in range(length):
            destination[i] = swap_bytes_uint16(rgba8_to_rgb5a3(source[i]))

        return destination_palette


class ImageBase(numpy.ndarray):

    def __init__(self, width, height):
        col_count = (width + self.tile_width - 1)//self.tile_width
        row_count = (height + self.tile_height - 1)//self.tile_height
        super().__init__((row_count, col_count), self.tile_type)
        self.width = width
        self.height = height


class ImageI4(ImageBase):
    image_format = gx.TF_I4
    tile_width = 8
    tile_height = 8
    tile_type = numpy.dtype((numpy.uint8, (8, 4)))

    def decode_to_i8(self, destination_image=None):
        if destination_image is None:
            destination_image = numpy.empty((self.height, self.width), numpy.uint8)

        cdef numpy.uint8_t[:,:,:,:] source = self
        cdef numpy.uint8_t[:,:] destination = destination_image
        cdef unsigned int height = destination.shape[0]
        cdef unsigned int width = destination.shape[1]
        cdef unsigned int i, j, texels

        for i in range(height):
            for j in range(0, width, 2):
                texels = source[i//8, j//8, i % 8, (j % 8)//2]
                destination[i,j] = cc48[(texels >> 4) & 0xF]
                if j + 1 >= width: break
                destination[i, j + 1] = cc48[texels & 0xF]

        return destination_image

    @classmethod
    def encode_from_i8(cls, source_image, destination_image=None):
        if destination_image is None:
            destination_image = cls(source_image.shape[1], source_image.shape[0])

        cdef numpy.uint8_t[:,:] source = source_image
        cdef numpy.uint8_t[:,:,:,:] destination = destination_image
        cdef unsigned int height = source.shape[0]
        cdef unsigned int width = source.shape[1]
        cdef unsigned int i, j, texels

        for i in range(height):
            for j in range(0, width, 2):
                texels = cc84[source[i,j]] << 4
                texels |= cc84[source[i, j + 1]] if j + 1 < width else 0
                destination[i//8, j//8, i % 8, (j % 8)//2] = texels

        return destination_image


class ImageI8(ImageBase):
    image_format = gx.TF_I8
    tile_width = 8
    tile_height = 4
    tile_type = numpy.dtype((numpy.uint8, (4, 8)))

    def decode_to_i8(self, destination_image=None):
        if destination_image is None:
            destination_image = numpy.empty((self.height, self.width), numpy.uint8)

        cdef numpy.uint8_t[:,:,:,:] source = self
        cdef numpy.uint8_t[:,:] destination = destination_image
        cdef unsigned int height = destination.shape[0]
        cdef unsigned int width = destination.shape[1]
        cdef unsigned int i, j

        for i in range(height):
            for j in range(width):
                destination[i,j] = source[i//4, j//8, i % 4, j % 8]

        return destination_image

    @classmethod
    def encode_from_i8(cls, source_image, destination_image=None):
        if destination_image is None:
            destination_image = cls(source_image.shape[1], source_image.shape[0])

        cdef numpy.uint8_t[:,:] source = source_image
        cdef numpy.uint8_t[:,:,:,:] destination = destination_image
        cdef unsigned int height = source.shape[0]
        cdef unsigned int width = source.shape[1]
        cdef unsigned int i, j

        for i in range(height):
            for j in range(width):
                destination[i//4, j//8, i% 4, j % 8] = source[i,j]

        return destination_image


class ImageIA4(ImageBase):
    image_format = gx.TF_IA4
    tile_width = 8
    tile_height = 4
    tile_type = numpy.dtype((numpy.uint8, (4, 8)))

    def decode_to_ia8(self, destination_image=None):
        if destination_image is None:
            destination_image = numpy.empty((self.height, self.width, 2), numpy.uint8)

        cdef numpy.uint8_t[:,:,:,:] source = self
        cdef numpy.uint8_t[:,:,:] destination = destination_image
        cdef unsigned int height = destination.shape[0]
        cdef unsigned int width = destination.shape[1]
        cdef unsigned int i, j, texel

        for i in range(height):
            for j in range(width):
                texel = source[i//4 ,j//8, i % 4, j % 8]
                destination[i,j,0] = cc48[texel & 0xF]
                destination[i,j,1] = cc48[(texel >> 4) & 0xF]

        return destination_image

    @classmethod
    def encode_from_ia8(cls, source_image, destination_image=None):
        if destination_image is None:
            destination_image = cls(source_image.shape[1], source_image.shape[0])

        cdef numpy.uint8_t[:,:,:] source = source_image
        cdef numpy.uint8_t[:,:,:,:] destination = destination_image
        cdef unsigned int height = source.shape[0]
        cdef unsigned int width = source.shape[1]
        cdef unsigned int i, j

        for i in range(height):
            for j in range(width):
                destination[i//4, j//8, i % 4, j % 8] = cc84[source[i,j,0]] | (cc84[source[i,j,1]] << 4)

        return destination_image


class ImageIA8(ImageBase):
    image_format = gx.TF_IA8
    tile_width = 4
    tile_height = 4
    tile_type = numpy.dtype((numpy.uint8, (4, 4, 2)))

    def decode_to_ia8(self, destination_image=None):
        if destination_image is None:
            destination_image = numpy.empty((self.height, self.width, 2), numpy.uint8)

        cdef numpy.uint8_t[:,:,:,:,:] source = self
        cdef numpy.uint8_t[:,:,:] destination = destination_image
        cdef unsigned int height = destination.shape[0]
        cdef unsigned int width = destination.shape[1]
        cdef unsigned int i, j

        for i in range(height):
            for j in range(width):
                swap_ia8(source[i//4, j//4, i % 4, j % 4], destination[i,j])

        return destination_image

    @classmethod
    def encode_from_ia8(cls, source_image, destination_image=None):
        if destination_image is None:
            destination_image = cls(source_image.shape[1], source_image.shape[0])

        cdef numpy.uint8_t[:,:,:] source = source_image
        cdef numpy.uint8_t[:,:,:,:,:] destination = destination_image
        cdef unsigned int height = source.shape[0]
        cdef unsigned int width = source.shape[1]
        cdef unsigned int i, j

        for i in range(height):
            for j in range(width):
                swap_ia8(source[i,j], destination[i//4, j//4, i % 4, j % 4])

        return destination_image


class ImageRGB565(ImageBase):
    image_format = gx.TF_RGB565
    tile_width = 4
    tile_height = 4
    tile_type = numpy.dtype((numpy.uint16, (4, 4))).newbyteorder('>')

    def decode_to_rgb565(self, destination_image=None):
        if destination_image is None:
            destination_image = numpy.empty((self.height, self.width), numpy.uint16)

        cdef numpy.uint16_t[:,:,:,:] source = reinterpret_native_endian(self)
        cdef numpy.uint16_t[:,:] destination = destination_image
        cdef unsigned int height = destination.shape[0]
        cdef unsigned int width = destination.shape[1]
        cdef unsigned int i, j

        for i in range(height):
            for j in range(width):
                destination[i,j] = swap_bytes_uint16(source[i//4, j//4, i % 4, j % 4])

        return destination_image

    @classmethod
    def encode_from_rgb565(cls, source_image, destination_image=None):
        if destination_image is None:
            destination_image = cls(source_image.shape[1], source_image.shape[0])

        cdef numpy.uint16_t[:,:] source = source_image
        cdef numpy.uint16_t[:,:,:,:] destination = reinterpret_native_endian(destination_image)
        cdef unsigned int height = source.shape[0]
        cdef unsigned int width = source.shape[1]
        cdef unsigned int i, j

        for i in range(height):
            for j in range(width):
                destination[i//4, j//4, i % 4, j % 4] = swap_bytes_uint16(source[i,j])

        return destination_image

    def decode_to_rgba8(self, destination_image=None):
        if destination_image is None:
            destination_image = numpy.empty((self.height, self.width, 4), numpy.uint8)

        cdef numpy.uint16_t[:,:,:,:] source = reinterpret_native_endian(self)
        cdef numpy.uint8_t[:,:,:] destination = destination_image
        cdef unsigned int height = destination.shape[0]
        cdef unsigned int width = destination.shape[1]
        cdef unsigned int i, j

        for i in range(height):
            for j in range(width):
                rgb565_to_rgba8(swap_bytes_uint16(source[i//4, j//4, i % 4, j % 4]), destination[i,j])

        return destination_image

    @classmethod
    def encode_from_rgba8(cls, source_image, destination_image=None):
        if destination_image is None:
            destination_image = cls(source_image.shape[1], source_image.shape[0])

        cdef numpy.uint8_t[:,:,:] source = source_image
        cdef numpy.uint16_t[:,:,:,:] destination = reinterpret_native_endian(destination_image)
        cdef unsigned int height = source.shape[0]
        cdef unsigned int width = source.shape[1]
        cdef unsigned int i, j

        for i in range(height):
            for j in range(width):
                destination[i//4, j//4, i % 4, j % 4] = swap_bytes_uint16(rgba8_to_rgb565(source[i,j]))

        return destination_image


class ImageRGB5A3(ImageBase):
    image_format = gx.TF_RGB5A3
    tile_width = 4
    tile_height = 4
    tile_type = numpy.dtype((numpy.uint16, (4, 4))).newbyteorder('>')

    def decode_to_rgba8(self, destination_image=None):
        if destination_image is None:
            destination_image = numpy.empty((self.height, self.width, 4), numpy.uint8)

        cdef numpy.uint16_t[:,:,:,:] source = reinterpret_native_endian(self)
        cdef numpy.uint8_t[:,:,:] destination = destination_image
        cdef unsigned int height = destination.shape[0]
        cdef unsigned int width = destination.shape[1]
        cdef unsigned int i, j

        for i in range(height):
            for j in range(width):
                rgb5a3_to_rgba8(swap_bytes_uint16(source[i//4, j//4, i % 4, j % 4]), destination[i,j])

        return destination_image

    @classmethod
    def decode_from_rgba8(cls, source_image, destination_image=None):
        if destination_image is None:
            destination_image = cls(source_image.shape[1], source_image.shape[0])

        cdef numpy.uint8_t[:,:,:] source = source_image
        cdef numpy.uint16_t[:,:,:,:] destination = reinterpret_native_endian(destination_image)
        cdef unsigned int height = source.shape[0]
        cdef unsigned int width = source.shape[1]
        cdef unsigned int i, j

        for i in range(height):
            for j in range(width):
                destination[i//4, j//4, i % 4, j % 4] = swap_bytes_uint16(rgba8_to_rgb5a3(source[i,j]))

        return destination_image


class ImageRGBA8(ImageBase):
    image_format = gx.TF_RGBA8
    tile_width = 4
    tile_height = 4
    tile_type = numpy.dtype((((numpy.uint8, 2), (4, 4)), 2))

    def decode_to_rgba8(self, destination_image=None):
        if destination_image is None:
            destination_image = numpy.empty((self.height, self.width, 4), numpy.uint8)

        cdef numpy.uint8_t[:,:,:,:,:,:] source = self
        cdef numpy.uint8_t[:,:,:] destination = destination_image
        cdef unsigned int height = destination.shape[0]
        cdef unsigned int width = destination.shape[1]
        cdef unsigned int i, j

        for i in range(height):
            for j in range(width):
                destination[i,j,0] = source[i//4, j//4, 0, i % 4, j % 4, 1]
                destination[i,j,1] = source[i//4, j//4, 1, i % 4, j % 4, 0]
                destination[i,j,2] = source[i//4, j//4, 1, i % 4, j % 4, 1]
                destination[i,j,3] = source[i//4, j//4, 0, i % 4, j % 4, 0]

        return destination_image

    @classmethod
    def encode_from_rgba8(cls, source_image, destination_image=None):
        if destination_image is None:
            destination_image = cls(source_image.shape[1], source_image.shape[0])

        cdef numpy.uint8_t[:,:,:] source = source_image
        cdef numpy.uint8_t[:,:,:,:,:,:] destination = destination_image
        cdef unsigned int height = source.shape[0]
        cdef unsigned int width = source.shape[1]
        cdef unsigned int i, j

        for i in range(height):
            for j in range(width):
                destination[i//4, j//4, 0, i % 4, j % 4, 1] = source[i,j,0]
                destination[i//4, j//4, 1, i % 4, j % 4, 0] = source[i,j,1]
                destination[i//4, j//4, 1, i % 4, j % 4, 1] = source[i,j,2]
                destination[i//4, j//4, 0, i % 4, j % 4, 0] = source[i,j,3]

        return destination_image


class ImageCMPR(ImageBase):
    image_format = gx.TF_CMPR
    tile_width = 8
    tile_height = 8
    tile_type = numpy.dtype((dxt1_block, (2, 2))).newbyteorder('>')

    def decode_to_rgba8(self, destination_image=None):
        if destination_image is None:
            destination_image = numpy.empty((self.height, self.width, 4), numpy.uint8)

        cdef dxt1_block_t[:,:,:,:] source = reinterpret_native_endian(self)
        cdef numpy.uint8_t[:,:,:] destination = destination_image
        cdef unsigned int height = destination.shape[0]
        cdef unsigned int width = destination.shape[1]
        cdef unsigned int i, j

        for i in range(0, height, 4):
            for j in range(0, width, 4):
                dxt1_decompress_block(swap_bytes_dxt1_block(source[i//8, j//8, (i % 8)//4, (j % 8)//4]), destination[i:(i + 4), j:(j + 4)])

        return destination_image


class ImageCI4(ImageBase):
    image_format = gx.TF_CI4
    tile_width = 8
    tile_height = 8
    tile_type = numpy.dtype((numpy.uint8, (8, 4)))

    def decode_to_ci8(self, destination_image=None):
        if destination_image is None:
            destination_image = numpy.empty((self.height, self.width), numpy.uint8)

        cdef numpy.uint8_t[:,:,:,:] source = self
        cdef numpy.uint8_t[:,:] destination = destination_image
        cdef unsigned int height = destination.shape[0]
        cdef unsigned int width = destination.shape[1]
        cdef unsigned int i, j, texels

        for i in range(height):
            for j in range(0, width, 2):
                texels = source[i//8, j//8, i % 8, (j % 8)//2]
                destination[i,j] = (texels >> 4) & 0xF
                if j + 1 >= width: break
                destination[i, j + 1] = texels & 0xF

        return destination_image

    @classmethod
    def encode_from_ci8(cls, source_image, destination_image=None):
        if destination_image is None:
            destination_image = cls(source_image.shape[1], source_image.shape[0])

        cdef numpy.uint8_t[:,:] source = source_image
        cdef numpy.uint8_t[:,:,:,:] destination = destination_image
        cdef unsigned int height = source.shape[0]
        cdef unsigned int width = source.shape[1]
        cdef unsigned int i, j, texels

        for i in range(height):
            for j in range(0, width, 2):
                texels = (source[i,j] << 4) & 0xF0
                texels |= (source[i, j + 1] & 0xF) if j + 1 < width else 0
                destination[i//8, j//8, i % 8, (j % 8)//2] = texels

        return destination_image

    def decode_to_direct_color(self, source_palette, destination_image=None):
        if destination_image is None:
            destination_image = numpy.empty((self.height, self.width) + source_palette.shape[1:], source_palette.dtype)

        cdef numpy.uint8_t[:,:,:,:] source = self
        cdef numpy.uint8_t[:,:] palette = reinterpret_elements(source_palette, numpy.uint8, 1)
        cdef numpy.uint8_t[:,:,:] destination = reinterpret_elements(destination_image, numpy.uint8, 2)
        cdef unsigned int height = destination.shape[0]
        cdef unsigned int width = destination.shape[1]
        cdef unsigned int i, j, texels

        for i in range(height):
            for j in range(0, width, 2):
                texels = source[i//8, j//8, i % 8, (j % 8)//2]
                destination[i,j] = palette[(texels >> 4) & 0xF]
                if j + 1 >= width: break
                destination[i, j + 1] = palette[texels & 0xF]

        return destination_image


class ImageCI8(ImageBase):
    image_format = gx.TF_CI8
    tile_width = 8
    tile_height = 4
    tile_type = numpy.dtype((numpy.uint8, (4, 8)))

    def decode_to_ci8(self, destination_image):
        if destination_image is None:
            destination_image = numpy.empty((self.height, self.width), numpy.uint8)

        cdef numpy.uint8_t[:,:,:,:] source = self
        cdef numpy.uint8_t[:,:] destination = destination_image
        cdef unsigned int height = destination.shape[0]
        cdef unsigned int width = destination.shape[1]
        cdef unsigned int i,j

        for i in range(height):
            for j in range(width):
                destination[i,j] = source[i//4, j//8, i % 4, j % 8]

        return destination_image

    @classmethod
    def encode_from_ci8(cls, source_image, destination_image=None):
        if destination_image is None:
            destination_image = cls(source_image.shape[1], source_image.shape[0])

        cdef numpy.uint8_t[:,:] source = source_image
        cdef numpy.uint8_t[:,:,:,:] destination = destination_image
        cdef unsigned int height = source.shape[0]
        cdef unsigned int width = source.shape[1]
        cdef unsigned int i, j

        for i in range(height):
            for j in range(width):
                destination[i//4, j//8, i % 4, j % 4] = source[i,j]

        return destination_image

    def decode_to_direct_color(self, source_palette, destination_image=None):
        if destination_image is None:
            destination_image = numpy.empty((self.height, self.width) + source_palette.shape[1:], source_palette.dtype)

        cdef numpy.uint8_t[:,:,:,:] source = self
        cdef numpy.uint8_t[:,:] palette = reinterpret_elements(source_palette, numpy.uint8, 1)
        cdef numpy.uint8_t[:,:,:] destination = reinterpret_elements(destination_image, numpy.uint8, 2)
        cdef unsigned int height = destination.shape[0]
        cdef unsigned int width = destination.shape[1]
        cdef unsigned int i, j

        for i in range(height):
            for j in range(width):
                destination[i,j] = palette[source[i//4, j//8, i % 4, j % 8]]

        return destination_image


class ImageCI14(ImageBase):
    image_format = gx.TF_CI14
    tile_width = 4
    tile_height = 4
    tile_type = numpy.dtype((numpy.uint16, (4, 4))).newbyteorder('>')

    def decode_to_direct_color(self, source_palette, destination_image=None):
        if destination_image is None:
            destination_image = numpy.empty((self.height, self.witdh) + source_palette.shape[1:], source_palette.dtype)

        cdef numpy.uint16_t[:,:,:,:] source = reinterpret_native_endian(self)
        cdef numpy.uint8_t[:,:] palette = reinterpret_elements(source_palette, numpy.uint8, 1)
        cdef numpy.uint8_t[:,:,:] destination = reinterpret_elements(destination_image, numpy.uint8, 2)
        cdef unsigned int height = destination.shape[0]
        cdef unsigned int width = destination.shape[1]
        cdef unsigned int i, j

        for i in range(height):
            for j in range(width):
                destination[i,j] = palette[source[i//4, j//8, i % 4, j % 8] & 0x3FFF]

        return destination_image


def pack_palette(stream, palette):
    palette.tofile(stream)


def unpack_palette(stream, palette_format, entry_count):
    if palette_format == gx.TL_IA8:
        palette_type = PaletteIA8
    elif palette_format == gx.TL_RGB565:
        palette_type = PaletteRGB565
    elif palette_format == gx.TL_RGB5A3:
        palette_type = PaletteRGB5A3
    else:
        raise ValueError('invalid palette format')

    palette = numpy.fromfile(stream, palette_type.entry_type, entry_count)
    return palette.view(palette_type)


def pack_images(stream, images):
    for image in images:
        image.tofile(stream)


def unpack_images(stream, image_format, base_width, base_height, level_count):
    if image_format == gx.TF_I4:
        image_type = ImageI4
    elif image_format == gx.TF_I8:
        image_type = ImageI8
    elif image_format == gx.TF_IA4:
        image_type = ImageIA4
    elif image_format == gx.TF_IA8:
        image_type = ImageIA8
    elif image_format == gx.TF_RGB565:
        image_type = ImageRGB565
    elif image_format == gx.TF_RGB5A3:
        image_type = ImageRGB5A3
    elif image_format == gx.TF_RGBA8:
        image_type = ImageRGBA8
    elif image_format == gx.TF_CI4:
        image_type = ImageCI4
    elif image_format == gx.TF_CI8:
        image_type = ImageCI8
    elif image_format == gx.TF_CI14:
        image_type = ImageCI14
    elif image_format == gx.TF_CMPR:
        image_type = ImageCMPR
    else:
        raise ValueError('invalid image format')

    images = [None]*level_count

    for level in range(level_count):
        width = max(base_width//(2**level), 1)
        height = max(base_height//(2**level), 1)

        col_count = (width + image_type.tile_width - 1)//image_type.tile_width
        row_count = (height + image_type.tile_height - 1)//image_type.tile_height
        image = numpy.fromfile(stream, image_type.tile_type, col_count*row_count)
        image = image.reshape((row_count, col_count) + image.shape[1:])
        image = image.view(image_type)
        image.width = width
        image.height = height

        images[level] = image

    return tuple(images)

