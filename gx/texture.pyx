#cython: boundscheck=False, wraparound=False, cdivision=True

import numpy
cimport numpy
from OpenGL.GL import *
import gl
import gx

import logging
logger = logging.getLogger(__name__)


cdef numpy.uint16_t swap_bytes_uint16(numpy.uint16_t i):
    return (i << 8) | (i >> 8)


cdef numpy.uint32_t swap_bytes_uint32(numpy.uint32_t i):
    return (i << 24) | ((i << 8) & 0xFF0000) | ((i >> 8) & 0xFF00) | (i >> 24)


def native_byteorder(array):
    return array.view(array.dtype.newbyteorder('<'))


cdef void rgb5a3_to_rgba8(numpy.uint16_t source,numpy.uint8_t[:] destination):
    source = swap_bytes_uint16(source)
    if source & 0x8000:
        destination[0] = ((source >> 7) & 0xF8) | ((source >> 12) & 0x7)
        destination[1] = ((source >> 2) & 0xF8) | ((source >> 7) & 0x7)
        destination[2] = ((source << 3) & 0xF8) | ((source >> 2) & 0x7)
        destination[3] = 0xFF
    else:
        destination[0] = ((source >> 4) & 0xF0) | ((source >> 8) & 0xF)
        destination[1] = (source & 0xF0) | ((source >> 4) & 0xF)
        destination[2] = ((source << 4) & 0xF0) | (source & 0xF)
        destination[3] = ((source >> 7) & 0xE0) | ((source >> 10) & 0x1C) | ((source >> 13) & 0x3)


def untile(source,destination):
    height = destination.shape[0]
    width = destination.shape[1]
    tile_height = source.shape[2]
    tile_width = source.shape[3]

    for i in range(min(tile_height,height)):
        for j in range(min(tile_width,width)):
            d = destination[i::tile_height,j::tile_width]
            d[:] = source[:d.shape[0],:d.shape[1],i,j]


dxt1_block = numpy.dtype([('color0',numpy.uint16),('color1',numpy.uint16),('indices',numpy.uint32)])


cdef packed struct dxt1_block_t:
    numpy.uint16_t color0
    numpy.uint16_t color1
    numpy.uint32_t indices


cdef void dxt1_decompress_block(dxt1_block_t block,numpy.uint8_t[:,:,:] destination):
    cdef numpy.uint16_t color0 = swap_bytes_uint16(block.color0)
    cdef numpy.uint16_t color1 = swap_bytes_uint16(block.color1)
    cdef numpy.uint32_t indices = swap_bytes_uint32(block.indices)
    cdef numpy.uint8_t color_table[4][4]
    cdef unsigned int i,j,index

    color_table[0][0] = ((color0 >> 8) & 0xF8) | ((color0 >> 11) & 0x7)
    color_table[0][1] = ((color0 >> 3) & 0xFC) | ((color0 >> 5) & 0x3)
    color_table[0][2] = ((color0 << 3) & 0xF8) | (color0 & 0x7)
    color_table[0][3] = 0xFF
    color_table[1][0] = ((color1 >> 8) & 0xF8) | ((color1 >> 11) & 0x7)
    color_table[1][1] = ((color1 >> 3) & 0xFC) | ((color1 >> 5) & 0x3)
    color_table[1][2] = ((color1 << 3) & 0xF8) | (color1 & 0x7)
    color_table[1][3] = 0xFF

    if color0 > color1:
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
            index = (indices >> (30 - 2*(4*i + j))) & 0x3
            destination[i,j,0] = color_table[index][0]
            destination[i,j,1] = color_table[index][1]
            destination[i,j,2] = color_table[index][2]
            destination[i,j,3] = color_table[index][3]


class HashableArray(numpy.ndarray):

    def __hash__(self):
        return object.__hash__(self)


class PaletteIA8(HashableArray):
    palette_format = gx.TL_IA8
    entry_type = numpy.dtype((numpy.uint8,2))
    gl_image_format = GL_UNSIGNED_BYTE
    gl_component_count = GL_RG
    gl_texel_type = numpy.dtype((numpy.uint8,2))
    gl_swizzle = numpy.array([GL_RED,GL_RED,GL_RED,GL_GREEN],numpy.int32)


class PaletteRGB565(HashableArray):
    palette_format = gx.TL_RGB565
    entry_type = numpy.dtype(numpy.uint16).newbyteorder('>')
    gl_image_format = GL_UNSIGNED_SHORT_5_6_5
    gl_component_count = GL_RGB
    gl_texel_type = numpy.uint16
    gl_swizzle = numpy.array([GL_RED,GL_GREEN,GL_BLUE,GL_ONE],numpy.int32)


class PaletteRGB5A3(HashableArray):
    palette_format = gx.TL_RGB5A3
    entry_type = numpy.dtype(numpy.uint16).newbyteorder('>')
    gl_image_format = GL_UNSIGNED_BYTE
    gl_component_count = GL_RGBA
    gl_texel_type = numpy.dtype((numpy.uint8,4))
    gl_swizzle = numpy.array([GL_RED,GL_GREEN,GL_BLUE,GL_ALPHA],numpy.int32)


class ImageI4(HashableArray):
    image_format = gx.TF_I4
    tile_width = 8
    tile_height = 8
    tile_type = numpy.dtype((numpy.uint8,(8,4)))
    gl_image_format = GL_UNSIGNED_BYTE
    gl_component_count = GL_RED
    gl_swizzle = numpy.array([GL_RED,GL_RED,GL_RED,GL_RED],numpy.int32)

    def gl_convert(self,palette):
        cdef unsigned int width = self.width
        cdef unsigned int height = self.height
        cdef numpy.uint8_t[:,:,:,:] self_view = self
        cdef numpy.ndarray[numpy.uint8_t,ndim=2] image = numpy.empty((height,width),numpy.uint8)
        cdef unsigned int i,j,texel

        for i in range(height):
            for j in range(0,width,2):
                texel = self_view[i//8,j//8,i % 8,(j//2) % 4]
                image[i,j] = (texel & 0xF0) | ((texel >> 4) & 0xF)
                if j + 1 >= width: break
                image[i,j + 1] = ((texel << 4) & 0xF0) | (texel & 0xF)

        return image


class ImageI8(HashableArray):
    image_format = gx.TF_I8
    tile_width = 8
    tile_height = 4
    tile_type = numpy.dtype((numpy.uint8,(4,8)))
    gl_image_format = GL_UNSIGNED_BYTE
    gl_component_count = GL_RED
    gl_swizzle = numpy.array([GL_RED,GL_RED,GL_RED,GL_RED],numpy.int32)

    def gl_convert(self,palette):
        image = numpy.empty((self.height,self.width),numpy.uint8)
        untile(self,image)
        return image


class ImageIA4(HashableArray):
    image_format = gx.TF_IA4
    tile_width = 8
    tile_height = 4
    tile_type = numpy.dtype((numpy.uint8,(4,8)))
    gl_image_format = GL_UNSIGNED_BYTE
    gl_component_count = GL_RG
    gl_swizzle = numpy.array([GL_RED,GL_RED,GL_RED,GL_GREEN],numpy.int32)

    def gl_convert(self,palette):
        cdef unsigned int width = self.width
        cdef unsigned int height = self.height
        cdef numpy.uint8_t[:,:,:,:] self_view = self
        cdef numpy.ndarray[numpy.uint8_t,ndim=3] image = numpy.empty((height,width,2),numpy.uint8)
        cdef unsigned int i,j,texel

        for i in range(height):
            for j in range(width):
                texel = self_view[i//4,j//8,i % 4,j % 8]
                image[i,j,0] = ((texel << 4) & 0xF0) | (texel & 0xF)
                image[i,j,1] = (texel & 0xF0) | ((texel >> 4) & 0xF)

        return image


class ImageIA8(HashableArray):
    image_format = gx.TF_IA8
    tile_width = 4
    tile_height = 4
    tile_type = numpy.dtype((numpy.uint8,(4,4,2)))
    gl_image_format = GL_UNSIGNED_BYTE
    gl_component_count = GL_RG
    gl_swizzle = numpy.array([GL_RED,GL_RED,GL_RED,GL_GREEN],numpy.int32)

    def gl_convert(self,palette):
        image = numpy.empty((self.height,self.width,2),numpy.uint8)
        untile(self[:,:,:,:,0],image[:,:,1])
        untile(self[:,:,:,:,1],image[:,:,0])
        return image


class ImageRGB565(HashableArray):
    image_format = gx.TF_RGB565
    tile_width = 4
    tile_height = 4
    tile_type = numpy.dtype((numpy.uint16,(4,4))).newbyteorder('>')
    gl_image_format = GL_UNSIGNED_SHORT_5_6_5
    gl_component_count = GL_RGB
    gl_swizzle = numpy.array([GL_RED,GL_GREEN,GL_BLUE,GL_ONE],numpy.int32)

    def gl_convert(self,palette):
        image = numpy.empty((self.height,self.width),numpy.uint16)
        untile(self,image)
        return image


class ImageRGB5A3(HashableArray):
    image_format = gx.TF_RGB5A3
    tile_width = 4
    tile_height = 4
    tile_type = numpy.dtype((numpy.uint16,(4,4))).newbyteorder('>')
    gl_image_format = GL_UNSIGNED_BYTE
    gl_component_count = GL_RGBA
    gl_swizzle = numpy.array([GL_RED,GL_GREEN,GL_BLUE,GL_ALPHA],numpy.int32)

    def gl_convert(self,palette):
        cdef unsigned int width = self.width
        cdef unsigned int height = self.height
        cdef numpy.uint16_t[:,:,:,:] self_view = native_byteorder(self)
        cdef numpy.ndarray[numpy.uint8_t,ndim=3] image = numpy.empty((height,width,4),numpy.uint8)
        cdef unsigned int i,j,texel

        for i in range(height):
            for j in range(width):
                rgb5a3_to_rgba8(self_view[i//4,j//4,i % 4,j % 4],image[i,j])

        return image


class ImageRGBA8(HashableArray):
    image_format = gx.TF_RGBA8
    tile_width = 4
    tile_height = 4
    tile_type = numpy.dtype((((numpy.uint8,2),(4,4)),2))
    gl_image_format = GL_UNSIGNED_BYTE
    gl_component_count = GL_RGBA
    gl_swizzle = numpy.array([GL_RED,GL_GREEN,GL_BLUE,GL_ALPHA],numpy.int32)

    def gl_convert(self,palette):
        image = numpy.empty((self.height,self.width,4),numpy.uint8)
        untile(self[:,:,0,:,:,0],image[:,:,3])
        untile(self[:,:,0,:,:,1],image[:,:,0])
        untile(self[:,:,1,:,:,0],image[:,:,1])
        untile(self[:,:,1,:,:,1],image[:,:,2])
        return image


class ImageCMPR(HashableArray):
    image_format = gx.TF_CMPR
    tile_width = 8
    tile_height = 8
    tile_type = numpy.dtype((dxt1_block,(2,2))).newbyteorder('>')
    gl_image_format = GL_UNSIGNED_BYTE
    gl_component_count = GL_RGBA
    gl_swizzle = numpy.array([GL_RED,GL_GREEN,GL_BLUE,GL_ALPHA],numpy.int32)

    def gl_convert(self,palette):
        cdef unsigned int width = self.width
        cdef unsigned int height = self.height
        cdef dxt1_block_t[:,:,:,:] self_view = native_byteorder(self)
        cdef numpy.ndarray[numpy.uint8_t,ndim=3] image = numpy.empty((height,width,4),numpy.uint8)
        cdef numpy.uint8_t[:,:,:] image_view = image
        cdef dxt1_block_t block
        cdef unsigned int i,j

        for i in range(0,height,4):
            for j in range(0,width,4):
                block = self_view[i//8,j//8,(i//4) % 2,(j//4) % 2]
                dxt1_decompress_block(block,image_view[i:min(i + 4,height),j:min(j + 4,width)])

        return image


cdef gl_convert_ci4_ia8(numpy.uint8_t[:,:,:,:] self_view,unsigned int width,unsigned int height,numpy.uint8_t[:,:] palette):
    cdef numpy.ndarray[numpy.uint8_t,ndim=3] image = numpy.empty((height,width,2),numpy.uint8)
    cdef unsigned int i,j,texel

    for i in range(height):
        for j in range(width):
            texel = self_view[i//8,j//8,i % 8,(j//2) % 4]
            image[i,j] = palette[(texel >> 4) & 0xF]
            if j + 1 >= width: break
            image[i,j + 1] = palette[texel & 0xF]

    return image


cdef gl_convert_ci4_rgb565(numpy.uint8_t[:,:,:,:] self_view,unsigned int width,unsigned int height,numpy.uint16_t[:] palette):
    cdef numpy.ndarray[numpy.uint16_t,ndim=2] image = numpy.empty((height,width),numpy.uint16)
    cdef unsigned int i,j,texel

    for i in range(height):
        for j in range(width):
            texel = self_view[i//8,j//8,i % 8,(j//2) % 4]
            image[i,j] = swap_bytes_uint16(palette[(texel >> 4) & 0xF])
            if j + 1 >= width: break
            image[i,j + 1] = swap_bytes_uint16(palette[texel & 0xF])

    return image


cdef gl_convert_ci4_rgb5a3(numpy.uint8_t[:,:,:,:] self_view,unsigned int width,unsigned int height,numpy.uint16_t[:] palette):
    cdef numpy.ndarray[numpy.uint8_t,ndim=3] image = numpy.empty((height,width,4),numpy.uint8)
    cdef unsigned int i,j,texel

    for i in range(height):
        for j in range(width):
            texel = self_view[i//8,j//8,i % 8,(j//2) % 4]
            rgb5a3_to_rgba8(palette[(texel >> 4) & 0xF],image[i,j])
            if j + 1 >= width: break
            rgb5a3_to_rgba8(palette[texel & 0xF],image[i,j + 1])

    return image


cdef gl_convert_ci8_ia8(numpy.uint8_t[:,:,:,:] self_view,unsigned int width,unsigned int height,numpy.uint8_t[:,:] palette):
    cdef numpy.ndarray[numpy.uint8_t,ndim=3] image = numpy.empty((height,width,2),numpy.uint8)
    cdef unsigned int i,j

    for i in range(height):
        for j in range(width):
            image[i,j] = palette[self_view[i//4,j//4,i % 4,j % 4]]

    return image


cdef gl_convert_ci8_rgb565(numpy.uint8_t[:,:,:,:] self_view,unsigned int width,unsigned int height,numpy.uint16_t[:] palette):
    cdef numpy.ndarray[numpy.uint16_t,ndim=2] image = numpy.empty((height,width),numpy.uint16)
    cdef unsigned int i,j

    for i in range(height):
        for j in range(width):
            image[i,j] = swap_bytes_uint16(palette[self_view[i//4,j//4,i % 4,j % 4]])

    return image


cdef gl_convert_ci8_rgb5a3(numpy.uint8_t[:,:,:,:] self_view,unsigned int width,unsigned int height,numpy.uint16_t[:] palette):
    cdef numpy.ndarray[numpy.uint8_t,ndim=3] image = numpy.empty((height,width,4),numpy.uint8)
    cdef unsigned int i,j,texel

    for i in range(height):
        for j in range(width):
            rgb5a3_to_rgba8(palette[self_view[i//4,j//4,i % 4,j % 4]],image[i,j])

    return image


cdef gl_convert_ci14_ia8(numpy.uint16_t[:,:,:,:] self_view,unsigned int width,unsigned int height,numpy.uint8_t[:,:] palette):
    cdef numpy.ndarray[numpy.uint8_t,ndim=3] image = numpy.empty((height,width,2),numpy.uint8)
    cdef unsigned int i,j

    for i in range(height):
        for j in range(width):
            image[i,j] = palette[swap_bytes_uint16(self_view[i//4,j//8,i % 4,j % 8]) & 0x3FFF]

    return image


cdef gl_convert_ci14_rgb565(numpy.uint16_t[:,:,:,:] self_view,unsigned int width,unsigned int height,numpy.uint16_t[:] palette):
    cdef numpy.ndarray[numpy.uint16_t,ndim=2] image = numpy.empty((height,width),numpy.uint16)
    cdef unsigned int i,j

    for i in range(height):
        for j in range(width):
            image[i,j] = swap_bytes_uint16(palette[swap_bytes_uint16(self_view[i//4,j//8,i % 4,j % 8]) & 0x3FFF])

    return image


cdef gl_convert_ci14_rgb5a3(numpy.uint16_t[:,:,:,:] self_view,unsigned int width,unsigned int height,numpy.uint16_t[:] palette):
    cdef numpy.ndarray[numpy.uint8_t,ndim=3] image = numpy.empty((height,width,4),numpy.uint8)
    cdef unsigned int i,j

    for i in range(height):
        for j in range(width):
            rgb5a3_to_rgba8(palette[swap_bytes_uint16(self_view[i//4,j//8,i % 4,j % 8]) & 0x3FFF],image[i,j])

    return image


class ImageCI4(HashableArray):
    image_format = gx.TF_CI4
    tile_width = 8
    tile_height = 8
    tile_type = numpy.dtype((numpy.uint8,(8,4)))

    def gl_convert(self,palette):
        if palette.palette_format == gx.TL_IA8:
            return gl_convert_ci4_ia8(self,self.width,self.height,palette)
        if palette.palette_format == gx.TL_RGB565:
            return gl_convert_ci4_rgb565(self,self.width,self.height,native_byteorder(palette))
        if palette.palette_format == gx.TL_RGB5A3:
            return gl_convert_ci4_rgb5a3(self,self.width,self.height,native_byteorder(palette))

        raise ValueError('invalid palette format')


class ImageCI8(HashableArray):
    image_format = gx.TF_CI8
    tile_width = 8
    tile_height = 4
    tile_type = numpy.dtype((numpy.uint8,(4,8)))

    def gl_convert(self,palette):
        if palette.palette_format == gx.TL_IA8:
            return gl_convert_ci8_ia8(self,self.width,self.height,palette)
        if palette.palette_format == gx.TL_RGB565:
            return gl_convert_ci8_rgb565(self,self.width,self.height,native_byteorder(palette))
        if palette.palette_format == gx.TL_RGB5A3:
            return gl_convert_ci8_rgb5a3(self,self.width,self.height,native_byteorder(palette))

        raise ValueError('invalid palette format')


class ImageCI14(HashableArray):
    image_format = gx.TF_CI14
    tile_width = 4
    tile_height = 4
    tile_type = numpy.dtype((numpy.uint16,(4,4))).newbyteorder('>')

    def gl_convert(self,palette):
        if palette.palette_format == gx.TL_IA8:
            return gl_convert_ci14_ia8(native_byteorder(self),self.width,self.height,palette)
        if palette.palette_format == gx.TL_RGB565:
            return gl_convert_ci14_rgb565(native_byteorder(self),self.width,self.height,native_byteorder(palette))
        if palette.palette_format == gx.TL_RGB5A3:
            return gl_convert_ci14_rgb5a3(native_byteorder(self),self.width,self.height,native_byteorder(palette))

        raise ValueError('invalid palette format')


def pack_palette(stream,palette):
    palette.tofile(stream)


def unpack_palette(stream,palette_format,entry_count):
    if palette_format == gx.TL_IA8:
        palette_type = PaletteIA8
    elif palette_format == gx.TL_RGB565:
        palette_type = PaletteRGB565
    elif palette_format == gx.TL_RGB5A3:
        palette_type = PaletteRGB5A3
    else:
        raise ValueError('invalid palette format')

    palette = numpy.fromfile(stream,palette_type.entry_type,entry_count)
    return palette.view(palette_type)


def pack_images(stream,images):
    for image in images:
        image.tofile(stream)


def unpack_images(stream,image_format,base_width,base_height,level_count):
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
        width = max(base_width//(2**level),1)
        height = max(base_height//(2**level),1)

        col_count = (width + image_type.tile_width - 1)//image_type.tile_width
        row_count = (height + image_type.tile_height - 1)//image_type.tile_height
        image = numpy.fromfile(stream,image_type.tile_type,col_count*row_count)
        image = image.reshape((row_count,col_count) + image.shape[1:])
        image = image.view(image_type)
        image.width = width
        image.height = height

        images[level] = image

    return tuple(images)


class GLTexture(gl.Texture):

    def __init__(self,images,palette):
        super().__init__()

        glBindTexture(GL_TEXTURE_2D,self)
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_BASE_LEVEL,0)
        glTexParameteri(GL_TEXTURE_2D,GL_TEXTURE_MAX_LEVEL,len(images) - 1)

        if images[0].image_format in {gx.TF_CI4,gx.TF_CI8,gx.TF_CI14}:
            component_count = palette.gl_component_count
            image_format = palette.gl_image_format
            swizzle = palette.gl_swizzle
        else:
            component_count = images[0].gl_component_count
            image_format = images[0].gl_image_format
            swizzle = images[0].gl_swizzle

        glTexParameteriv(GL_TEXTURE_2D,GL_TEXTURE_SWIZZLE_RGBA,swizzle)

        for level,image in enumerate(images):
            glTexImage2D(GL_TEXTURE_2D,level,component_count,image.width,image.height,0,component_count,image_format,image.gl_convert(palette))


class Texture:

    def __init__(self):
        self.wrap_s = gx.CLAMP
        self.wrap_t = gx.CLAMP
        self.minification_filter = gx.NEAR
        self.magnification_filter = gx.NEAR
        self.minimum_lod = 0
        self.maximum_lod = 0
        self.lod_bias = 0
        self.images = None
        self.palette = None

    def gl_init(self,texture_factory=GLTexture):
        self.gl_wrap_s_need_update = True
        self.gl_wrap_t_need_update = True
        self.gl_minification_filter_need_update = True
        self.gl_magnification_filter_need_update = True
        self.gl_minimum_lod_need_update = True
        self.gl_maximum_lod_need_update = True
        self.gl_lod_bias_need_update = True

        self.gl_sampler = gl.Sampler()
        self.gl_texture = texture_factory(self.images,self.palette)

    def gl_bind(self,texture_unit):
        if self.gl_wrap_s_need_update:
            glSamplerParameteri(self.gl_sampler,GL_TEXTURE_WRAP_S,self.wrap_s.gl_value)
            self.gl_wrap_s_need_update = False
        if self.gl_wrap_t_need_update:
            glSamplerParameteri(self.gl_sampler,GL_TEXTURE_WRAP_T,self.wrap_t.gl_value)
            self.gl_wrap_t_need_update = False
        if self.gl_minification_filter_need_update:
            glSamplerParameteri(self.gl_sampler,GL_TEXTURE_MIN_FILTER,self.minification_filter.gl_value)
            self.gl_minification_filter_need_update = False
        if self.gl_magnification_filter_need_update:
            glSamplerParameteri(self.gl_sampler,GL_TEXTURE_MAG_FILTER,self.magnification_filter.gl_value)
            self.gl_magnification_filter_need_update = False
        if self.gl_minimum_lod_need_update:
            glSamplerParameterf(self.gl_sampler,GL_TEXTURE_MIN_LOD,self.minimum_lod)
            self.gl_minimum_lod_need_update = False
        if self.gl_maximum_lod_need_update:
            glSamplerParameterf(self.gl_sampler,GL_TEXTURE_MAX_LOD,self.maximum_lod)
            self.gl_maximum_lod_need_update = False
        if self.gl_lod_bias_need_update:
            glSamplerParameterf(self.gl_sampler,GL_TEXTURE_LOD_BIAS,self.lod_bias)
            self.gl_lod_bias_need_update = False

        glBindSampler(texture_unit,self.gl_sampler)
        glActiveTexture(GL_TEXTURE0 + texture_unit)
        glBindTexture(GL_TEXTURE_2D,self.gl_texture)

