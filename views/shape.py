import numpy
from OpenGL.GL import *
import gl
import gx
import views

import logging
logger = logging.getLogger(__name__)


def gl_count_triangles(shape):
    triangle_count = 0

    for primitive in shape.primitives:
        if primitive.primitive_type == gx.TRIANGLES:
            triangle_count += len(primitive.vertices)//3
        elif primitive.primitive_type == gx.TRIANGLESTRIP:
            triangle_count += len(primitive.vertices) - 2
        elif primitive.primitive_type == gx.TRIANGLEFAN:
            triangle_count += len(primitive.vertices) - 2
        elif primitive.primitive_type == gx.QUADS:
            triangle_count += len(primitive.vertices)//2
        else:
            raise ValueError('invalid primitive type')
            
    return triangle_count

    
def gl_create_element_array(shape,element_map,element_count):
    element_array = numpy.empty(element_count,numpy.uint16)
    
    element_index = 0
    vertex_index = 0

    for primitive in shape.primitives:
        if primitive.primitive_type == gx.TRIANGLES:
            for i in range(len(primitive.vertices)//3):
                element_array[element_index + 0] = element_map[vertex_index + 3*i + 0]
                element_array[element_index + 1] = element_map[vertex_index + 3*i + 2]
                element_array[element_index + 2] = element_map[vertex_index + 3*i + 1]
                element_index += 3
        elif primitive.primitive_type == gx.TRIANGLESTRIP:
            for i in range(len(primitive.vertices) - 2):
                element_array[element_index + 0] = element_map[vertex_index + i + 1 - (i % 2)]
                element_array[element_index + 1] = element_map[vertex_index + i + (i % 2)]
                element_array[element_index + 2] = element_map[vertex_index + i + 2]
                element_index += 3
        elif primitive.primitive_type == gx.TRIANGLEFAN:
            for i in range(len(primitive.vertices) - 2):
                element_array[element_index + 0] = element_map[vertex_index]
                element_array[element_index + 1] = element_map[vertex_index + i + 2]
                element_array[element_index + 2] = element_map[vertex_index + i + 1]
                element_index += 3
        elif primitive.primitive_type == gx.QUADS:
            for i in range(0,len(primitive.vertices)//4,4):
                element_array[element_index + 0] = element_map[vertex_index + i]
                element_array[element_index + 1] = element_map[vertex_index + i + 1]
                element_array[element_index + 2] = element_map[vertex_index + i + 2]
                element_array[element_index + 3] = element_map[vertex_index + i + 1]
                element_array[element_index + 4] = element_map[vertex_index + i + 3]
                element_array[element_index + 5] = element_map[vertex_index + i + 2]
                element_index += 6
        else:
            raise ValueError('invalid primitive type')

        vertex_index += len(primitive.vertices)

    return element_array

    
class Shape(gl.ResourceManagerMixin, views.View):

    transformation_type = views.ReadOnlyAttribute()
    batches = views.ReadOnlyAttribute()
    attribute_descriptors = views.ReadOnlyAttribute()

    @property
    def attributes(self):
        for descriptor in self.attribute_descriptors:
            yield descriptor.attribute

    @property
    def primitives(self):
        for batch in self.batches:
            yield from batch.primitives

    def gl_init(self,array_table):
        self.gl_hide = False

        self.gl_vertex_array = self.gl_create_resource(gl.VertexArray)
        glBindVertexArray(self.gl_vertex_array)

        self.gl_vertex_buffer = self.gl_create_resource(gl.Buffer)
        glBindBuffer(GL_ARRAY_BUFFER,self.gl_vertex_buffer)

        self.gl_element_count = 3*gl_count_triangles(self)
        self.gl_element_buffer = self.gl_create_resource(gl.Buffer)
        glBindBuffer(GL_ELEMENT_ARRAY_BUFFER,self.gl_element_buffer)

        vertex_type =  numpy.dtype([array_table[attribute].field() for attribute in self.attributes])
        vertex_count = sum(len(primitive.vertices) for primitive in self.primitives)
        vertex_array = numpy.empty(vertex_count,vertex_type)

        for attribute in self.attributes:
            array_table[attribute].load(self,vertex_array)

        vertex_array,element_map = numpy.unique(vertex_array,return_inverse=True)
        element_array = gl_create_element_array(self,element_map,self.gl_element_count)

        glBufferData(GL_ARRAY_BUFFER,vertex_array.nbytes,vertex_array,GL_STATIC_DRAW)
        glBufferData(GL_ELEMENT_ARRAY_BUFFER,element_array.nbytes,element_array,GL_STATIC_DRAW)

    def gl_bind(self):
        glBindVertexArray(self.gl_vertex_array)

    def gl_draw(self):
        glDrawElements(GL_TRIANGLES,self.gl_element_count,GL_UNSIGNED_SHORT,None)

