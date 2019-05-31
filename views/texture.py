import numpy
from OpenGL.GL import *
import gl
import gx


class GLTexture(gl.Texture):

    def __init__(self, images, palette):
        super().__init__()

        if images[0].image_format in {gx.TF_I4, gx.TF_I8}:
            image_format = GL_UNSIGNED_BYTE
            component_count = GL_RED
            swizzle = [GL_RED, GL_RED, GL_RED, GL_RED]
            convert = lambda image: image.decode_to_i8()
        elif images[0].image_format in {gx.TF_IA4, gx.TF_IA8}:
            image_format = GL_UNSIGNED_BYTE
            component_count = GL_RG
            swizzle = [GL_RED, GL_RED, GL_RED, GL_GREEN]
            convert = lambda image: image.decode_to_ia8()
        elif images[0].image_format == gx.TF_RGB565:
            image_format = GL_UNSIGNED_SHORT_5_6_5
            component_count = GL_RGB
            swizzle = [GL_RED, GL_GREEN, GL_BLUE, GL_ONE]
            convert = lambda image: image.decode_to_rgb565()
        elif images[0].image_format in {gx.TF_RGB5A3, gx.TF_RGBA8, gx.TF_CMPR}:
            image_format = GL_UNSIGNED_BYTE
            component_count = GL_RGBA
            swizzle = [GL_RED, GL_GREEN, GL_BLUE, GL_ALPHA]
            convert = lambda image: image.decode_to_rgba8()
        elif images[0].image_format in {gx.TF_CI4, gx.TF_CI8, gx.TF_CI14}:
            if palette.palette_format == gx.TL_IA8:
                image_format = GL_UNSIGNED_BYTE
                component_count = GL_RG
                swizzle = [GL_RED, GL_RED, GL_RED, GL_GREEN]
                palette = palette.decode_to_ia8()
            elif palette.palette_format == gx.TL_RGB565:
                image_format = GL_UNSIGNED_SHORT_5_6_5
                component_count = GL_RGB
                swizzle = [GL_RED, GL_GREEN, GL_BLUE, GL_ONE]
                palette = palette.decode_to_rgb565()
            elif palette.palette_format == gx.TL_RGB5A3:
                image_format = GL_UNSIGNED_BYTE
                component_count = GL_RGBA
                swizzle = [GL_RED, GL_GREEN, GL_BLUE, GL_ALPHA]
                palette = palette.decode_to_rgba8()
            else:
                raise ValueError('invalid palette format')
            convert = lambda image: image.decode_to_direct_color(palette)
        else:
            raise ValueError('invalid image format')

        glBindTexture(GL_TEXTURE_2D, self)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_BASE_LEVEL, 0)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAX_LEVEL, len(images) - 1)
        glTexParameteriv(GL_TEXTURE_2D, GL_TEXTURE_SWIZZLE_RGBA, numpy.array(swizzle, numpy.int32))

        for level,image in enumerate(images):
            glTexImage2D(GL_TEXTURE_2D, level, component_count, image.width, image.height, 0, component_count, image_format, convert(image))


class Texture(gl.ResourceOwner):

    def __init__(self, base):
        super().__init__()
        self.base = base
        self.gl_sampler = self.gl_create(gl.Sampler)
        self.gl_texture = self.gl_create(GLTexture, base.images, base.palette)

    def __getattr__(self, name):
        return getattr(self.base, name)
    
    @property
    def images(self):
        return self.base.images

    @property
    def width(self):
        return self.images[0].width
        
    @property
    def height(self):
        return self.images[0].height
        
    @property
    def image_format(self):
        return self.images[0].image_format

    def gl_bind(self, texture_unit):
        glSamplerParameteri(self.gl_sampler, GL_TEXTURE_WRAP_S, self.wrap_s.gl_value)
        glSamplerParameteri(self.gl_sampler, GL_TEXTURE_WRAP_T, self.wrap_t.gl_value)
        glSamplerParameteri(self.gl_sampler, GL_TEXTURE_MIN_FILTER, self.minification_filter.gl_value)
        glSamplerParameteri(self.gl_sampler, GL_TEXTURE_MAG_FILTER, self.magnification_filter.gl_value)
        glSamplerParameterf(self.gl_sampler, GL_TEXTURE_MIN_LOD, self.minimum_lod)
        glSamplerParameterf(self.gl_sampler, GL_TEXTURE_MAX_LOD, self.maximum_lod)
        glSamplerParameterf(self.gl_sampler, GL_TEXTURE_LOD_BIAS, self.lod_bias)

        glBindSampler(texture_unit, self.gl_sampler)
        glActiveTexture(GL_TEXTURE0 + texture_unit)
        glBindTexture(GL_TEXTURE_2D, self.gl_texture)

