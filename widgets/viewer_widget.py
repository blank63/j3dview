from math import cos,sin,tan,radians
import os.path
import numpy
from OpenGL.GL import *
from PyQt5 import QtCore,QtWidgets
import qt
from views.material import MATRIX_BLOCK_BINDING_POINT
from views.vertex_shader import MatrixBlock

import logging
logger = logging.getLogger(__name__)


class Quarternion:

    def __init__(self,a=0,b=0,c=0,d=0):
        self.a = a
        self.b = b
        self.c = c
        self.d = d

    def __mul__(self,other):
        return Quarternion(
                self.a*other.a - self.b*other.b - self.c*other.c - self.d*other.d,
                self.a*other.b + self.b*other.a + self.c*other.d - self.d*other.c,
                self.a*other.c - self.b*other.d + self.c*other.a + self.d*other.b,
                self.a*other.d + self.b*other.c - self.c*other.b + self.d*other.a)

    def conjugate(self):
        return Quarternion(self.a,-self.b,-self.c,-self.d)

    @staticmethod
    def rotation(axis_x,axis_y,axis_z,angle):
        s = sin(angle/2)
        return Quarternion(cos(angle/2),s*axis_x,s*axis_y,s*axis_z)


def create_rotation_matrix(rotation):
    a,b,c,d = rotation.a,rotation.b,rotation.c,rotation.d
    return numpy.array([
        [a*a + b*b - c*c - d*d,2*(b*c - a*d),2*(b*d + a*c)],
        [2*(b*c + a*d),a*a - b*b + c*c - d*d,2*(c*d - a*b)],
        [2*(b*d - a*c),2*(c*d + a*b),a*a - b*b - c*c + d*d]],numpy.float32)


def create_frustum_matrix(left,right,bottom,top,near,far):
    return numpy.array([
        [2*near/(right - left),0,(right + left)/(right - left),0],
        [0,2*near/(top - bottom),(top + bottom)/(top - bottom),0],
        [0,0,-(far + near)/(far - near),-2*far*near/(far - near)],
        [0,0,-1,0]],
        numpy.float32)


class ViewerWidget(QtWidgets.QOpenGLWidget,metaclass=qt.PropertyOwnerMetaClass):

    z_near = qt.Property(float)
    z_far = qt.Property(float)
    fov = qt.Property(float)
    movement_speed = qt.Property(float)
    rotation_speed = qt.Property(float)

    @property
    def projection_matrix(self):
        return self.matrix_block['projection_matrix']

    @projection_matrix.setter
    def projection_matrix(self,matrix):
        self.matrix_block['projection_matrix'] = matrix

    @property
    def view_matrix(self):
        return self.matrix_block['view_matrix']

    @view_matrix.setter
    def view_matrix(self,matrix):
        self.matrix_block['view_matrix'] = matrix

    def __init__(self,*args):
        super().__init__(*args)

        self.setFocusPolicy(QtCore.Qt.StrongFocus)

        self.model = None
        self.animation = None

        self.z_near = 25
        self.z_far = 12800
        self.fov = 22.5
        self.view_position = numpy.array([0,0,1000],numpy.float32)
        self.view_rotation = Quarternion(1,0,0,0)
        self.movement_speed = 10
        self.rotation_speed = 1
        self.fps = 30

        self.z_near_changed.connect(self.on_z_near_changed)
        self.z_far_changed.connect(self.on_z_far_changed)
        self.fov_changed.connect(self.on_fov_changed)

        self.animation_timer = QtCore.QTimer(self)
        self.animation_timer.timeout.connect(self.on_animation_timer_timeout)

        self.pressed_keys = set()

        QtWidgets.qApp.aboutToQuit.connect(self.on_application_aboutToQuit)

    def update_projection_matrix(self):
        u = self.z_near*tan(radians(self.fov))
        r = u*self.width()/self.height()
        self.projection_matrix = create_frustum_matrix(-r,r,-u,u,self.z_near,self.z_far)
        self.projection_matrix_need_update = False

    def update_view_matrix(self):
        #FIXME: Renormalise rotation occasionally
        self.view_matrix[:,0:3] = create_rotation_matrix(self.view_rotation)
        self.view_matrix[:,3] = -numpy.dot(self.view_matrix[:,0:3],self.view_position)
        self.view_matrix_need_update = False

    def initializeGL(self):
        logger.info('OpenGL vendor: %s',glGetString(GL_VENDOR).decode())
        logger.info('OpenGL renderer: %s',glGetString(GL_RENDERER).decode())
        logger.info('OpenGL version: %s',glGetString(GL_VERSION).decode())
        logger.info('OpenGLSL version: %s',glGetString(GL_SHADING_LANGUAGE_VERSION).decode())

        if self.format().samples() > 1:
            glEnable(GL_MULTISAMPLE)

        self.matrix_block = MatrixBlock(GL_DYNAMIC_DRAW)
        self.projection_matrix_need_update = True
        self.view_matrix_need_update = True

        self.animation_timer.start(1000/self.fps)

    def paintGL(self):
        glClearColor(0.5,0.5,0.5,1)
        glClearDepth(1.0)
        glDepthMask(True)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        if self.model is not None:
            self.matrix_block.bind(MATRIX_BLOCK_BINDING_POINT)
            self.model.gl_draw()

    def resizeGL(self,width,height):
        glViewport(0,0,width,height)
        self.projection_matrix_need_update = True

    def sizeHint(self):
        return QtCore.QSize(640,480)

    @QtCore.pyqtSlot(float)
    def on_z_near_changed(self,value):
        self.projection_matrix_need_update = True

    @QtCore.pyqtSlot(float)
    def on_z_far_changed(self,value):
        self.projection_matrix_need_update = True

    @QtCore.pyqtSlot(float)
    def on_fov_changed(self,value):
        self.projection_matrix_need_update = True

    @QtCore.pyqtSlot()
    def on_animation_timer_timeout(self):
        if QtWidgets.qApp.keyboardModifiers() & QtCore.Qt.ShiftModifier:
            movement_speed = 5*self.movement_speed
            rotation_speed = 5*self.rotation_speed
        else:
            movement_speed = self.movement_speed
            rotation_speed = self.rotation_speed

        if QtCore.Qt.Key_A in self.pressed_keys and QtCore.Qt.Key_D not in self.pressed_keys:
            self.view_position -= movement_speed*self.view_matrix[0,0:3]
            self.view_matrix_need_update = True
        if QtCore.Qt.Key_D in self.pressed_keys and QtCore.Qt.Key_A not in self.pressed_keys:
            self.view_position += movement_speed*self.view_matrix[0,0:3]
            self.view_matrix_need_update = True
        if QtCore.Qt.Key_Q in self.pressed_keys and QtCore.Qt.Key_E not in self.pressed_keys:
            self.view_position -= movement_speed*self.view_matrix[1,0:3]
            self.view_matrix_need_update = True
        if QtCore.Qt.Key_E in self.pressed_keys and QtCore.Qt.Key_Q not in self.pressed_keys:
            self.view_position += movement_speed*self.view_matrix[1,0:3]
            self.view_matrix_need_update = True
        if QtCore.Qt.Key_W in self.pressed_keys and QtCore.Qt.Key_S not in self.pressed_keys:
            self.view_position -= movement_speed*self.view_matrix[2,0:3]
            self.view_matrix_need_update = True
        if QtCore.Qt.Key_S in self.pressed_keys and QtCore.Qt.Key_W not in self.pressed_keys:
            self.view_position += movement_speed*self.view_matrix[2,0:3]
            self.view_matrix_need_update = True

        if QtCore.Qt.Key_J in self.pressed_keys and QtCore.Qt.Key_L not in self.pressed_keys:
            self.view_rotation = Quarternion.rotation(0,1,0,-radians(rotation_speed))*self.view_rotation
            self.view_matrix_need_update = True
        if QtCore.Qt.Key_L in self.pressed_keys and QtCore.Qt.Key_J not in self.pressed_keys:
            self.view_rotation = Quarternion.rotation(0,1,0,radians(rotation_speed))*self.view_rotation
            self.view_matrix_need_update = True
        if QtCore.Qt.Key_I in self.pressed_keys and QtCore.Qt.Key_K not in self.pressed_keys:
            self.view_rotation = Quarternion.rotation(1,0,0,-radians(rotation_speed))*self.view_rotation
            self.view_matrix_need_update = True
        if QtCore.Qt.Key_K in self.pressed_keys and QtCore.Qt.Key_I not in self.pressed_keys:
            self.view_rotation = Quarternion.rotation(1,0,0,radians(rotation_speed))*self.view_rotation
            self.view_matrix_need_update = True
        if QtCore.Qt.Key_O in self.pressed_keys and QtCore.Qt.Key_U not in self.pressed_keys:
            self.view_rotation = Quarternion.rotation(0,0,1,-radians(rotation_speed))*self.view_rotation
            self.view_matrix_need_update = True
        if QtCore.Qt.Key_U in self.pressed_keys and QtCore.Qt.Key_O not in self.pressed_keys:
            self.view_rotation = Quarternion.rotation(0,0,1,radians(rotation_speed))*self.view_rotation
            self.view_matrix_need_update = True

        if self.projection_matrix_need_update:
            self.update_projection_matrix()

        if self.view_matrix_need_update:
            self.update_view_matrix()

        if self.animation is not None and not self.animation.is_finished:
            self.animation.advance_frame()

        self.update()

    def setModel(self,model):
        self.makeCurrent()
        model = model
        model.gl_init()
        self.model = model
        self.animation = None

    def setAnimation(self,animation):
        animation.attach(self.model)
        self.animation = animation

    def keyPressEvent(self,event):
        self.pressed_keys.add(event.key())
        super().keyPressEvent(event)

    def keyReleaseEvent(self,event):
        self.pressed_keys.discard(event.key())
        super().keyPressEvent(event)

    def focusOutEvent(self,event):
        self.pressed_keys = set()
        super().focusOutEvent(event)

    @QtCore.pyqtSlot()
    def on_application_aboutToQuit(self):
        #XXX Delete OpenGL objects before the OpenGL module starts to unload
        #FIXME: Find a better way of doing this?
        self.makeCurrent()
        if hasattr(self,'matrix_block'): del self.matrix_block
        if hasattr(self,'model'): del self.model

