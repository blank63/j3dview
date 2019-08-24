import numpy
from OpenGL.GL import *
import gl
import gx


class LazyProperty:

    def __init__(self, fget):
        self.fget = fget

    def __get__(self, obj, cls):
        value = self.fget(obj)
        setattr(obj, self.fget.__name__, value)
        return value


class Texture(gl.ResourceOwner):

    def __init__(self, base):
        super().__init__()
        self.base = base
        self.reload()
        self.callbacks = []

    def register(self, callback):
        self.callbacks.append(callback)

    def unregister(self, callback):
        self.callbacks.remove(callback)

    def reload(self):
        self.name = self.base.name
        self.wrap_s = self.base.wrap_s
        self.wrap_t = self.base.wrap_t
        self.minification_filter = self.base.minification_filter
        self.magnification_filter = self.base.magnification_filter
        self.minimum_lod = self.base.minimum_lod
        self.maximum_lod = self.base.maximum_lod
        self.lod_bias = self.base.lod_bias
        self.unknown0 = self.base.unknown0
        self.unknown1 = self.base.unknown1
        self.unknown2 = self.base.unknown2
        self.gl_sampler_invalidate()

    def commit(self):
        self.base.name = self.name
        self.base.wrap_s = self.wrap_s
        self.base.wrap_t = self.wrap_t
        self.base.minification_filter = self.minification_filter
        self.base.magnification_filter = self.magnification_filter
        self.base.minimum_lod = self.minimum_lod
        self.base.maximum_lod = self.maximum_lod
        self.base.lod_bias = self.lod_bias
        self.base.unknown0 = self.unknown0
        self.base.unknown1 = self.unknown1
        self.base.unknown2 = self.unknown2
        
        for callback in self.callbacks:
            callback()

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

    @property
    def palette(self):
        return self.base.palette

    @property
    def palette_format(self):
        return self.palette.palette_format

    @property
    def gl_wrap_s(self):
        if self.wrap_s == gx.CLAMP:
            return GL_CLAMP_TO_EDGE
        if self.wrap_s == gx.REPEAT:
            return GL_REPEAT
        if self.wrap_s == gx.MIRROR:
            return GL_MIRRORED_REPEAT
        raise ValueError('Invalid wrap: {}'.format(self.wrap_s))

    @property
    def gl_wrap_t(self):
        if self.wrap_t == gx.CLAMP:
            return GL_CLAMP_TO_EDGE
        if self.wrap_t == gx.REPEAT:
            return GL_REPEAT
        if self.wrap_t == gx.MIRROR:
            return GL_MIRRORED_REPEAT
        raise ValueError('Invalid wrap: {}'.format(self.wrap_t))

    @property
    def gl_minification_filter(self):
        if self.minification_filter == gx.NEAR:
            return GL_LINEAR
        if self.minification_filter == gx.LINEAR:
            return GL_LINEAR
        if self.minification_filter == gx.NEAR_MIP_NEAR:
            return GL_NEAREST_MIPMAP_NEAREST
        if self.minification_filter == gx.LIN_MIP_NEAR:
            return GL_LINEAR_MIPMAP_NEAREST
        if self.minification_filter == gx.NEAR_MIP_LIN:
            return GL_NEAREST_MIPMAP_LINEAR
        if self.minification_filter == gx.LIN_MIP_LIN:
            return GL_LINEAR_MIPMAP_LINEAR
        raise ValueError('Invalid minification filter: {}'.format(self.minification_filter))

    @property
    def gl_magnification_filter(self):
        if self.magnification_filter == gx.NEAR:
            return GL_LINEAR
        if self.magnification_filter == gx.LINEAR:
            return GL_LINEAR
        raise ValueError('Invalid magnification filter: {}'.format(self.magnification_filter))

    @LazyProperty
    def _gl_sampler(self):
        return self.gl_create(gl.Sampler)

    @LazyProperty
    def gl_sampler(self):
        glSamplerParameteri(self._gl_sampler, GL_TEXTURE_WRAP_S, self.gl_wrap_s)
        glSamplerParameteri(self._gl_sampler, GL_TEXTURE_WRAP_T, self.gl_wrap_t)
        glSamplerParameteri(self._gl_sampler, GL_TEXTURE_MIN_FILTER, self.gl_minification_filter)
        glSamplerParameteri(self._gl_sampler, GL_TEXTURE_MAG_FILTER, self.gl_magnification_filter)
        glSamplerParameterf(self._gl_sampler, GL_TEXTURE_MIN_LOD, self.minimum_lod)
        glSamplerParameterf(self._gl_sampler, GL_TEXTURE_MAX_LOD, self.maximum_lod)
        glSamplerParameterf(self._gl_sampler, GL_TEXTURE_LOD_BIAS, self.lod_bias)
        return self._gl_sampler

    def gl_sampler_invalidate(self):
        try:
            del self.gl_sampler
        except AttributeError:
            pass

    @LazyProperty
    def gl_texture(self):
        if self.image_format in {gx.TF_I4, gx.TF_I8}:
            image_format = GL_UNSIGNED_BYTE
            component_count = GL_RED
            swizzle = [GL_RED, GL_RED, GL_RED, GL_RED]
            convert = lambda image: image.decode_to_i8()
        elif self.image_format in {gx.TF_IA4, gx.TF_IA8}:
            image_format = GL_UNSIGNED_BYTE
            component_count = GL_RG
            swizzle = [GL_RED, GL_RED, GL_RED, GL_GREEN]
            convert = lambda image: image.decode_to_ia8()
        elif self.image_format == gx.TF_RGB565:
            image_format = GL_UNSIGNED_SHORT_5_6_5
            component_count = GL_RGB
            swizzle = [GL_RED, GL_GREEN, GL_BLUE, GL_ONE]
            convert = lambda image: image.decode_to_rgb565()
        elif self.image_format in {gx.TF_RGB5A3, gx.TF_RGBA8, gx.TF_CMPR}:
            image_format = GL_UNSIGNED_BYTE
            component_count = GL_RGBA
            swizzle = [GL_RED, GL_GREEN, GL_BLUE, GL_ALPHA]
            convert = lambda image: image.decode_to_rgba8()
        elif self.image_format in {gx.TF_CI4, gx.TF_CI8, gx.TF_CI14}:
            if self.palette_format == gx.TL_IA8:
                image_format = GL_UNSIGNED_BYTE
                component_count = GL_RG
                swizzle = [GL_RED, GL_RED, GL_RED, GL_GREEN]
                palette = self.palette.decode_to_ia8()
            elif self.palette_format == gx.TL_RGB565:
                image_format = GL_UNSIGNED_SHORT_5_6_5
                component_count = GL_RGB
                swizzle = [GL_RED, GL_GREEN, GL_BLUE, GL_ONE]
                palette = self.palette.decode_to_rgb565()
            elif self.palette_format == gx.TL_RGB5A3:
                image_format = GL_UNSIGNED_BYTE
                component_count = GL_RGBA
                swizzle = [GL_RED, GL_GREEN, GL_BLUE, GL_ALPHA]
                palette = self.palette.decode_to_rgba8()
            else:
                raise ValueError('Invalid palette format: {}'.format(self.palette_format))
            convert = lambda image: image.decode_to_direct_color(self.palette)
        else:
            raise ValueError('Invalid image format: {}'.format(self.image_format))

        texture = self.gl_create(gl.Texture)
        glBindTexture(GL_TEXTURE_2D, texture)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_BASE_LEVEL, 0)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAX_LEVEL, len(self.images) - 1)
        glTexParameteriv(GL_TEXTURE_2D, GL_TEXTURE_SWIZZLE_RGBA, numpy.array(swizzle, numpy.int32))

        for level,image in enumerate(self.images):
            glTexImage2D(GL_TEXTURE_2D, level, component_count, image.width, image.height, 0, component_count, image_format, convert(image))

        return texture

    def gl_bind(self, texture_unit):
        glBindSampler(texture_unit, self.gl_sampler)
        glActiveTexture(GL_TEXTURE0 + texture_unit)
        glBindTexture(GL_TEXTURE_2D, self.gl_texture)

