#!/usr/bin/env python3

if __name__ == '__main__':
    # Logging and OpenGL have to be configured before OpenGL.GL is imported
    import io
    import logging
    import OpenGL

    stderr_handler = logging.StreamHandler()
    stderr_handler.setLevel(logging.WARNING)
    logging_stream = io.StringIO()
    logging_stream_handler = logging.StreamHandler(logging_stream)
    logging.basicConfig(level=logging.DEBUG,handlers=[stderr_handler,logging_stream_handler])

    OpenGL.ERROR_ON_COPY = True
    OpenGL.STORE_POINTERS = False
    OpenGL.FORWARD_COMPATIBLE_ONLY = True
    
import os.path
import numpy
from OpenGL.GL import *
from PyQt4 import QtCore,QtGui,QtOpenGL,uic
import j3d.model
import j3d.animation

import logging
logger = logging.getLogger(__name__)


class PreviewWidget(QtOpenGL.QGLWidget):

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.texture = None

    @QtCore.pyqtSlot(object)
    def setTexture(self,texture):
        self.texture = texture
        self.updateGL()

    def paintGL(self):
        glClearColor(0,0,0,1)
        glClear(GL_COLOR_BUFFER_BIT)
        if self.texture is not None and self.height() != 0 and self.width() != 0:
            s = self.width()/self.height()*self.texture.height/self.texture.width
            if s < 1:
                self.drawTexture(QtCore.QRectF(-1,-s,2,2*s),self.texture.gl_texture)
            else:
                s = self.height()/self.width()*self.texture.width/self.texture.height
                self.drawTexture(QtCore.QRectF(-s,-1,2*s,2),self.texture.gl_texture)

    def resizeGL(self,width,height):
        glViewport(0,0,width,height)


class Editor(QtGui.QMainWindow):

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)

        self.undo_stack = QtGui.QUndoStack(self,objectName='undo_stack')
        self.action_undo = self.undo_stack.createUndoAction(self)
        self.action_redo = self.undo_stack.createRedoAction(self)

        self.ui = uic.loadUi('ui/Editor.ui',self)

        self.menu_edit.addAction(self.action_undo)
        self.menu_edit.addAction(self.action_redo)

        self.menu_window.addAction(self.dock_view_settings.toggleViewAction())
        self.menu_window.addAction(self.dock_explorer.toggleViewAction())
        self.menu_window.addAction(self.dock_preview.toggleViewAction())
        self.menu_window.addAction(self.dock_texture.toggleViewAction())

        self.action_open_model.setShortcut(QtGui.QKeySequence.Open)
        self.action_save_model.setShortcut(QtGui.QKeySequence.Save)
        self.action_save_model_as.setShortcut(QtGui.QKeySequence.SaveAs)
        self.action_quit.setShortcut(QtGui.QKeySequence.Quit)
        self.action_undo.setShortcut(QtGui.QKeySequence.Undo)
        self.action_redo.setShortcut(QtGui.QKeySequence.Redo)

        self.view_settings.setViewer(self.viewer)
        self.dock_view_settings.hide()

        self.preview = PreviewWidget(shareWidget=self.viewer)
        self.dock_preview.setWidget(self.preview)

        self.texture.setUndoStack(self.undo_stack)

        self.action_open_animation.setEnabled(False)
        self.action_save_model.setEnabled(False)
        self.action_save_model_as.setEnabled(False)

        self.setWindowFilePath('')

        self.adjustSize()

        #self.readSettings()

    def windowFilePath(self):
        if not self.has_window_file_path:
            return ''
        return super().windowFilePath()

    def setWindowFilePath(self,path):
        if path == '':
            self.has_window_file_path = False
            super().setWindowFilePath('[No File]')
        else:
            self.has_window_file_path = True
            super().setWindowFilePath(path)

    def warning(self,message):
        QtGui.QMessageBox.warning(self,QtGui.qApp.applicationName(),message)

    def load(self,file_name):
        try:
            with open(file_name,'rb') as stream:
                model = j3d.model.unpack(stream)
        except (FileNotFoundError,IsADirectoryError,PermissionError) as error:
            self.warning('Could not open file \'{}\': {}'.format(file_name,error.strerror))
            return

        self.undo_stack.clear()

        self.model = model
        self.viewer.setModel(model)
        self.explorer.setModel(model)

        self.action_open_animation.setEnabled(True)
        self.action_save_model.setEnabled(True)
        self.action_save_model_as.setEnabled(True)

        self.setWindowFilePath(file_name)

    def save(self,file_name):
        try:
            with open(file_name,'wb') as stream:
                j3d.model.pack(stream,self.model,os.path.splitext(file_name)[1].lower())
        except (FileNotFoundError,IsADirectoryError,PermissionError) as error:
            self.warning('Could not save file \'{}\': {}'.format(file_name,error.strerror))
            return

        self.undo_stack.setClean()
        self.setWindowFilePath(file_name)

    def loadAnimation(self,file_name):
        try:
            with open(file_name,'rb') as stream:
                animation = j3d.animation.unpack(stream)
        except (FileNotFoundError,IsADirectoryError,PermissionError) as error:
            self.warning('Could not open file \'{}\': {}'.format(file_name,error.strerror))
            return

        try:
            self.viewer.setAnimation(animation)
        except j3d.animation.IncompatibleAnimationError:
            self.warning('Incompatible animation')

    def writeSettings(self):
        settings = QtCore.QSettings()

        settings.setValue('geometry',self.saveGeometry())
        settings.setValue('state',self.saveState())

        settings.beginGroup('view_settings')
        settings.setValue('z_near',self.viewer.z_near)
        settings.setValue('z_far',self.viewer.z_far)
        settings.setValue('fov',self.viewer.fov)
        settings.setValue('movement_speed',self.viewer.movement_speed)
        settings.setValue('rotation_speed',self.viewer.rotation_speed)
        settings.endGroup()

    def readSettings(self):
        settings = QtCore.QSettings()
        
        geometry = settings.value('geometry')
        if geometry is not None:
            self.restoreGeometry(geometry)

        state = settings.value('state')
        if state is not None:
            self.restoreState(state) #FIXME: Use versioning

        settings.beginGroup('view_settings')
        self.viewer.z_near = settings.value('z_near',25,float)
        self.viewer.z_far = settings.value('z_far',12800,float)
        self.viewer.fov = settings.value('fov',22.5,float)
        self.viewer.movement_speed = settings.value('movement_speed',10,float)
        self.viewer.rotation_speed = settings.value('rotation_speed',1,float)
        settings.endGroup()

    def closeEvent(self,event):
        #self.writeSettings()
        super().closeEvent(event)

    @QtCore.pyqtSlot(bool)
    def on_undo_stack_cleanChanged(self,clean):
        self.setWindowModified(not clean)

    @QtCore.pyqtSlot()
    def on_action_open_model_triggered(self):
        file_name = QtGui.QFileDialog.getOpenFileName(
                self,
                'Open Model',
                self.windowFilePath(),
                'Nintendo J3D model (*.bmd *.bdl);;All files (*)')
        if not file_name: return
        self.load(file_name)

    @QtCore.pyqtSlot()
    def on_action_open_animation_triggered(self):
        file_name = QtGui.QFileDialog.getOpenFileName(
                self,
                'Open Animation',
                os.path.dirname(self.windowFilePath()),
                'Nintendo J3D animation (*.bck *.btk *.btp *.bva *.brk *.bpk);;All files (*)')
        if not file_name: return
        self.loadAnimation(file_name)

    @QtCore.pyqtSlot()
    def on_action_save_model_triggered(self):
        self.save(self.windowFilePath())

    @QtCore.pyqtSlot()
    def on_action_save_model_as_triggered(self):
        file_name = QtGui.QFileDialog.getSaveFileName(
                self,
                'Save Model',
                self.windowFilePath(),
                'Nintendo J3D model (*.bmd *.bdl);;All files (*)')
        if not file_name: return
        self.save(file_name)

    @QtCore.pyqtSlot(object)
    def on_explorer_currentTextureChanged(self,texture):
        self.preview.setTexture(texture)
        self.texture.setTexture(texture)


if __name__ == '__main__':
    import sys
    import argparse

    def excepthook(*exception_info):
        logger.error('unexpected error',exc_info=exception_info)

        message = QtGui.QMessageBox(None)
        message.setWindowTitle(QtGui.qApp.applicationName())
        message.setIcon(QtGui.QMessageBox.Critical)
        message.setText('An unexpected error occurred.')
        message.setDetailedText(logging_stream.getvalue())
        message.setStandardButtons(QtGui.QMessageBox.Ok)
        message.setDefaultButton(QtGui.QMessageBox.Ok)
        message.exec_()

        QtGui.qApp.exit()

    logger.info('Python version: %s',sys.version)
    logger.info('NumPy version: %s',numpy.version.version)
    logger.info('Qt version: %s',QtCore.QT_VERSION_STR)
    logger.info('PyQt version: %s',QtCore.PYQT_VERSION_STR)
    logger.info('PyOpenGL version: %s',OpenGL.__version__)

    application = QtGui.QApplication(sys.argv)
    application.setOrganizationName('BlankSoft')
    application.setApplicationName('J3D View')

    sys.excepthook = excepthook

    parser = argparse.ArgumentParser(description='View Nintendo GameCube/Wii BMD/BDL files')
    parser.add_argument('file_name',nargs='?',metavar='file',help='file to view')
    #arguments = parser.parse_args(application.arguments()[1:]) #FIXME Doesn't work on Windows
    arguments = parser.parse_args()

    editor = Editor()
    editor.show()

    if arguments.file_name is not None:
        editor.load(arguments.file_name)

    application.exec_()

