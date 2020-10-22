from io import StringIO
from OpenGL.GL import *
import gl
import gx


MATRIX_INDEX_ATTRIBUTE_LOCATION = 0
POSITION_ATTRIBUTE_LOCATION = 1
NORMAL_ATTRIBUTE_LOCATION = 2
BINORMAL_ATTRIBUTE_LOCATION = 3
TANGENT_ATTRIBUTE_LOCATION = 4
COLOR_ATTRIBUTE_LOCATION = 5
TEXCOORD_ATTRIBUTE_LOCATIONS = [6,7,8,9,10,11,12,13]

ATTRIBUTE_LOCATION_TABLE = {
        gx.VA_PTNMTXIDX:MATRIX_INDEX_ATTRIBUTE_LOCATION,
        gx.VA_POS:POSITION_ATTRIBUTE_LOCATION,
        gx.VA_NRM:NORMAL_ATTRIBUTE_LOCATION,
        gx.VA_CLR0:COLOR_ATTRIBUTE_LOCATION,
        gx.VA_CLR1:COLOR_ATTRIBUTE_LOCATION,
        gx.VA_TEX0:TEXCOORD_ATTRIBUTE_LOCATIONS[0],
        gx.VA_TEX1:TEXCOORD_ATTRIBUTE_LOCATIONS[2],
        gx.VA_TEX2:TEXCOORD_ATTRIBUTE_LOCATIONS[2],
        gx.VA_TEX3:TEXCOORD_ATTRIBUTE_LOCATIONS[3],
        gx.VA_TEX4:TEXCOORD_ATTRIBUTE_LOCATIONS[4],
        gx.VA_TEX5:TEXCOORD_ATTRIBUTE_LOCATIONS[5],
        gx.VA_TEX6:TEXCOORD_ATTRIBUTE_LOCATIONS[6],
        gx.VA_TEX7:TEXCOORD_ATTRIBUTE_LOCATIONS[7]}


class MatrixBlock(gl.UniformBlock):
    projection_matrix = gl.mat4
    view_matrix = gl.mat4x3


def convert_material_source(source,index):
    if source == gx.SRC_VTX:
        return 'color'
    elif source == gx.SRC_REG:
        return 'material_color{}'.format(index)
    else:
        raise ValueError('invalid material source')


def convert_ambient_source(source,index):
    if source == gx.SRC_VTX:
        return 'color'
    elif source == gx.SRC_REG:
        return 'ambient_color{}'.format(index)
    else:
        raise ValueError('invalid ambient source')


def write_channel(stream,index,channel):
    material_color = convert_material_source(channel.color_mode.material_source,index)
    material_alpha = convert_material_source(channel.alpha_mode.material_source,index)

    stream.write('channel{} = vec4('.format(index))

    #XXX Lighting can't be properly implemented as BMD/BDL files doesn't
    # store any light information, but this seems to work pretty well
    if channel.color_mode.light_enable:
        ambient_color = convert_ambient_source(channel.color_mode.ambient_source,index)
        stream.write('0.5*({}.rgb + vec3(1.0))*'.format(ambient_color))
        #stream.write('clamp({}.rgb + vec3(0.3),0.0,1.0)*'.format(ambient_color))

    stream.write('{}.rgb,{}.a);\n'.format(material_color,material_alpha))


def write_identity_texcoord_generator(stream,generator):
    if generator.source == gx.TG_POS:
        source = 'position.xyz'
    elif generator.source == gx.TG_NRM:
        source = 'normal'
    elif generator.source == gx.TG_BINRM:
        source = 'binormal'
    elif generator.source == gx.TG_TANGENT:
        source = 'tangent'
    elif generator.source in gx.TG_TEX:
        source = 'vec3(texcoord{}, 1.0)'.format(generator.source.index)
    else:
        source = 'vec3(1.0)'

    stream.write(source)


def write_matrix_texcoord_generator(stream,generator,texture_matrices):
    if generator.source == gx.TG_POS:
        source = 'position'
    elif generator.source == gx.TG_NRM:
        source = 'vec4(normal,1.0)'
    elif generator.source == gx.TG_BINRM:
        source = 'vec4(binormal,1.0)'
    elif generator.source == gx.TG_TANGENT:
        source = 'vec4(tangent,1.0)'
    elif generator.source in gx.TG_TEX:
        source = 'vec4(texcoord{},1.0,1.0)'.format(generator.source.index)
    else:
        raise ValueError('invalid texture coordinate generator source')

    matrix_index = generator.matrix.index
    matrix = texture_matrices[matrix_index]

    #if matrix.shape != generator.function:
    #    raise ValueError() #<-?

    stream.write('texture_matrix{}*'.format(matrix_index))
    if matrix.matrix_type in {0x06,0x07}:
        stream.write('vec4(view_matrix*vec4({}.xyz,0.0),1.0)'.format(source))
    elif matrix.matrix_type == 0x09:
        stream.write('vec4(view_matrix*{},1.0)'.format(source))
    else:
        stream.write(source)


def write_texcoord_generator(stream,index,generator,texture_matrices):
    stream.write('generated_texcoord{} = '.format(index))

    if generator.function in {gx.TG_MTX2x4,gx.TG_MTX3x4}:
        if generator.matrix == gx.IDENTITY:
            write_identity_texcoord_generator(stream,generator)
        else:
            write_matrix_texcoord_generator(stream,generator,texture_matrices)
    elif generator.function in gx.TG_BUMP:
        if generator.source not in gx.TG_TEXCOORD:
            stream.write('vec3(1.0)')
        else:
            source_index = gx.TG_TEXCOORD.index(generator.source)
            if source_index >= index:
                stream.write('vec3(1.0)')
            else:
                stream.write('generated_texcoord{}'.format(source_index))
    elif generator.function == gx.TG_SRTG:
        if generator.source not in gx.TG_COLOR:
            stream.write('vec3(1.0)')
        else:
            source_index = gx.TG_COLOR.index(generator.source)
            stream.write('vec3(channel{}.rg, 1.0)'.format(source_index))
    else:
        raise ValueError('invalid texture coordinate generator function')

    stream.write(';\n')


def create_shader_string(material, transformation_type):
    stream = StringIO()

    stream.write('#version 330\n')

    stream.write('{}\n'.format(MatrixBlock.glsl_type))
    stream.write('{}\n'.format(material.gl_block.glsl_type))

    if transformation_type == 0:
        stream.write('uniform int matrix_index;\n')
        stream.write('uniform samplerBuffer matrix_table;\n')
        stream.write('#define MATRIX_ROW(i) texelFetch(matrix_table,3*matrix_index + i)\n')
        position = 'view_matrix*vec4(dot(MATRIX_ROW(0),position),dot(MATRIX_ROW(1),position),dot(MATRIX_ROW(2),position),1.0)'
    elif transformation_type == 1:
        position = '(position.xyz + view_matrix[3])'
    elif transformation_type == 2:
        raise Exception('y billboard matrix not implemented') #TODO
    elif transformation_type == 3:
        stream.write('layout(location={}) in int matrix_index;\n'.format(MATRIX_INDEX_ATTRIBUTE_LOCATION))
        stream.write('uniform samplerBuffer matrix_table;\n')
        stream.write('#define MATRIX_ROW(i) texelFetch(matrix_table,3*matrix_index + i)\n')
        position = 'view_matrix*vec4(dot(MATRIX_ROW(0),position),dot(MATRIX_ROW(1),position),dot(MATRIX_ROW(2),position),1.0)'
    else:
        raise ValueError('invalid matrix type')

    stream.write('layout(location={}) in vec4 position;\n'.format(POSITION_ATTRIBUTE_LOCATION))

    if material.use_normal:
        stream.write('layout(location={}) in vec3 normal;\n'.format(NORMAL_ATTRIBUTE_LOCATION))

    if material.use_binormal:
        stream.write('layout(location={}) in vec3 binormal;\n'.format(BINORMAL_ATTRIBUTE_LOCATION))

    if material.use_tangent:
        stream.write('layout(location={}) in vec3 tangent;\n'.format(TANGENT_ATTRIBUTE_LOCATION))

    if material.use_color:
        stream.write('layout(location={}) in vec4 color;\n'.format(COLOR_ATTRIBUTE_LOCATION))

    for i in range(8):
        if not material.use_texcoord[i]: continue
        stream.write('layout(location={}) in vec2 texcoord{};\n'.format(TEXCOORD_ATTRIBUTE_LOCATIONS[i],i))

    for i,channel in enumerate(material.enabled_channels):
        stream.write('out vec4 channel{};\n'.format(i))

    for i,generator in enumerate(material.enabled_texcoord_generators):
        stream.write('out vec3 generated_texcoord{};\n'.format(i))

    stream.write('\nvoid main()\n{\n')
    stream.write('gl_Position = projection_matrix*vec4({},1.0);\n'.format(position))

    for i,channel in enumerate(material.channels):
        if i < material.channel_count:
            write_channel(stream,i,channel)
        else:
            stream.write('const vec4 channel{} = vec4(1.0);\n'.format(i))

    for i,generator in enumerate(material.enabled_texcoord_generators):
        write_texcoord_generator(stream,i,generator,material.texture_matrices)

    stream.write('}\n')

    return stream.getvalue()

