import numpy
from OpenGL.GL import *


class Resource(GLuint):

    def __hash__(self):
        return object.__hash__(self)

    def __int__(self):
        return self.value

    def __index__(self):
        return self.value


class Buffer(Resource):

    def __init__(self):
        glGenBuffers(1,self)

    def __del__(self):
        glDeleteBuffers(1,self)


class VertexArray(Resource):

    def __init__(self):
        glGenVertexArrays(1,self)

    def __del__(self):
        glDeleteVertexArrays(1,self)

def VertexArray(): return glGenVertexArrays(1)


class Shader(Resource):

    def __init__(self,shader_type,source):
        super().__init__(glCreateShader(shader_type))

        glShaderSource(self,source)
        glCompileShader(self)

        if not glGetShaderiv(self,GL_COMPILE_STATUS):
            raise RuntimeError('Compile failure: {}{}'.format(glGetShaderInfoLog(self).decode(),source))

    def __del__(self):
        glDeleteShader(self)


class Program(Resource):

    def __init__(self,*shaders):
        super().__init__(glCreateProgram())

        for shader in shaders:
            glAttachShader(self,shader)

        glLinkProgram(self)

        if not glGetProgramiv(self,GL_LINK_STATUS):
            raise RuntimeError('Link failure: {}'.format(glGetProgramInfoLog(self).decode()))

        for shader in shaders:
            glDetachShader(self,shader)

    def __del__(self):
        glDeleteProgram(self)


class Texture(Resource):

    def __init__(self):
        super().__init__(glGenTextures(1))

    def __del__(self):
        glDeleteTextures(self.value)


class Sampler(Resource):

    def __init__(self):
        super().__init__(glGenSamplers(1))

    def __del__(self):
        glDeleteSamplers(1,self)


class Renderbuffer(Resource):

    def __init__(self):
        glGenRenderbuffers(1,self)

    def __del__(self):
        glDeleteRenderbuffers(1,self)


class Framebuffer(Resource):

    def __init__(self):
        glGenFramebuffers(1,self)

    def __del__(self):
        glDeleteFramebuffers(1,self)


class ChangeRegisteringArray(numpy.ndarray):
    #XXX Should only be changed using __setitem__

    def __array_finalize__(self,obj):
        if obj is None:
            self.changed = True

    def __setitem__(self,*args):
        if self.base is None:
            self.changed = True
        else:
            self.base.changed = True
        super().__setitem__(*args)


class ManagedBuffer:

    def __init__(self,target,usage,*args,**kwargs):
        super().__init__()
        self.target = target
        self.usage = usage
        self.data = ChangeRegisteringArray(*args,**kwargs)
        self.buffer = Buffer()
        glBindBuffer(target,self.buffer)
        glBufferData(target,self.data.nbytes,None,usage)

    def __getitem__(self,key):
        return self.data[key]

    def __setitem__(self,key,value):
        self.data[key] = value

    def __iter__(self):
        return iter(self.data)

    def sync_data(self):
        if self.data.changed:
            glBindBuffer(self.target,self.buffer)
            glBufferSubData(self.target,0,self.data.nbytes,self.data.view(numpy.ndarray))
            self.data.changed = False

    def bind(self,binding_point=None):
        if binding_point is None:
            glBindBuffer(self.target,self.buffer)
        else:
            glBindBufferBase(self.target,binding_point,self.buffer)

        if self.data.changed:
            glBufferSubData(self.target,0,self.data.nbytes,self.data.view(numpy.ndarray))
            self.data.changed = False


class TextureBuffer(ManagedBuffer):

    def __init__(self,usage,element_type,*args,**kwargs):
        super().__init__(GL_TEXTURE_BUFFER,usage,*args,**kwargs)
        self.element_type = element_type
        self.texture = Texture()

    def bind_texture(self,texture_unit):
        self.sync_data()
        glActiveTexture(GL_TEXTURE0 + texture_unit)
        glBindTexture(GL_TEXTURE_BUFFER,self.texture)
        glTexBuffer(GL_TEXTURE_BUFFER,self.element_type,self.buffer)


class Type:

    def __init__(self,glsl_type,numpy_type):
        self.glsl_type = glsl_type
        self.numpy_type = numpy_type

        if not numpy_type.shape:
            self.base_alignment = 4
        elif len(numpy_type.shape) == 1:
            self.base_alignment = 16 if numpy_type.shape[0] != 2 else 8
        else:
            self.base_alignment = 16
            if numpy_type.shape[-1] % 4 != 0:
                raise Exception('unaligned array elements not implemented')


vec2 = Type('vec2',numpy.dtype((numpy.float32,2)))
vec3 = Type('vec3',numpy.dtype((numpy.float32,3)))
vec4 = Type('vec4',numpy.dtype((numpy.float32,4)))
mat3x2 = Type('mat3x2',numpy.dtype((numpy.float32,(2,4)))) #TODO
mat4x2 = Type('mat4x2',numpy.dtype((numpy.float32,(2,4))))
mat4x3 = Type('mat4x3',numpy.dtype((numpy.float32,(3,4))))
mat4 = Type('mat4',numpy.dtype((numpy.float32,(4,4))))


class UniformBlockClassDictionary(dict):

    def __init__(self):
        super().__init__()
        self.glsl_fields = []
        self.numpy_fields = []
        self.offset = 0

    def add_field(self,name,field_type):
        if self.offset % field_type.base_alignment != 0:
            raise Exception('unaligned fields not implemented')
        self.glsl_fields.append('{} {};'.format(field_type.glsl_type,name))
        self.numpy_fields.append((name,field_type.numpy_type))
        self.offset += field_type.numpy_type.itemsize

    def __setitem__(self,key,value):
        if not key[:2] == key[-2:] == '__' and not hasattr(value,'__get__'):
            self.add_field(key,value)
        else:
            super().__setitem__(key,value)


class UniformBlockMetaClass(type):

    @classmethod
    def __prepare__(metacls,cls,bases):
        return UniformBlockClassDictionary()

    def __new__(metacls,cls,bases,classdict):
        uniform_block_class = type.__new__(metacls,cls,bases,classdict)
        uniform_block_class.glsl_type = (
                'layout(std140,row_major) uniform {}\n'.format(cls) +
                '{\n' +
                ''.join('    {}\n'.format(field) for field in classdict.glsl_fields) +
                '};')
        uniform_block_class.numpy_type = numpy.dtype(classdict.numpy_fields)
        return uniform_block_class


class UniformBlock(ManagedBuffer,metaclass=UniformBlockMetaClass):

    def __init__(self,usage):
        super().__init__(GL_UNIFORM_BUFFER,usage,1,self.numpy_type)

    def __getitem__(self,key):
        return super().__getitem__(key)[0]

    def __setitem__(self,key,value):
        super().__getitem__(key)[0] = value


def uniform_block(class_name,fields):
    bases = (UniformBlock,)
    classdict = UniformBlockMetaClass.__prepare__(class_name,bases)
    
    for name,field_type in fields:
        classdict[name] = field_type

    return UniformBlockMetaClass(class_name,bases,classdict)

