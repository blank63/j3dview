import io
import pkgutil
import os.path
from PyQt5 import QtCore, QtWidgets, QtGui, uic
import qt
import gx
import gx.bti
import j3d.model
import j3d.animation
import views.model
import widgets.explorer_widget


FILE_OPEN_ERRORS = (FileNotFoundError, IsADirectoryError, PermissionError)


class ReplaceTextureCommand(QtWidgets.QUndoCommand):
    #TODO: Should something be done about textures that are no longer being
    # used, but are still in the undo stack?

    def __init__(self, view, index, texture):
        super().__init__('Replace Texture')
        self.view = view
        self.index = index
        self.old_texture = view.viewed_object.textures[index]
        self.new_texture = texture

    def redo(self):
        self.view.replace_texture(self.index, self.new_texture)

    def undo(self):
        self.view.replace_texture(self.index, self.old_texture)


class Editor(QtWidgets.QMainWindow):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.undo_stack = QtWidgets.QUndoStack(self, objectName='undo_stack')
        self.action_undo = self.undo_stack.createUndoAction(self)
        self.action_redo = self.undo_stack.createRedoAction(self)

        self.ui = uic.loadUi(io.BytesIO(pkgutil.get_data(__package__, 'Editor.ui')), self)

        self.menu_edit.addAction(self.action_undo)
        self.menu_edit.addAction(self.action_redo)

        self.menu_window.addAction(self.dock_view_settings.toggleViewAction())
        self.menu_window.addAction(self.dock_explorer.toggleViewAction())
        self.menu_window.addAction(self.dock_preview.toggleViewAction())
        self.menu_window.addAction(self.dock_material_form.toggleViewAction())
        self.menu_window.addAction(self.dock_texture_form.toggleViewAction())

        self.action_open_model.setShortcut(QtGui.QKeySequence.Open)
        self.action_save_model.setShortcut(QtGui.QKeySequence.Save)
        self.action_save_model_as.setShortcut(QtGui.QKeySequence.SaveAs)
        self.action_quit.setShortcut(QtGui.QKeySequence.Quit)
        self.action_undo.setShortcut(QtGui.QKeySequence.Undo)
        self.action_redo.setShortcut(QtGui.QKeySequence.Redo)

        #XXX It appears that actions have to be manually added to the widget
        # for shortcuts to work. Possibly a bug?
        self.addAction(self.action_open_model)
        self.addAction(self.action_save_model)
        self.addAction(self.action_save_model_as)
        self.addAction(self.action_quit)
        self.addAction(self.action_undo)
        self.addAction(self.action_redo)

        self.action_open_animation.setEnabled(False)
        self.action_save_model.setEnabled(False)
        self.action_save_model_as.setEnabled(False)

        self.view_settings.setViewer(self.viewer)
        self.dock_view_settings.hide()
        self.tabifyDockWidget(self.dock_material_form, self.dock_texture_form)

        self.texture_form.undo_stack = self.undo_stack

        self.setWindowFilePath('')

        self.adjustSize()

        #self.readSettings()

        self.model = None

    def windowFilePath(self):
        if not self.has_window_file_path:
            return ''
        return super().windowFilePath()

    def setWindowFilePath(self, path):
        if path == '':
            self.has_window_file_path = False
            super().setWindowFilePath('[No File]')
        else:
            self.has_window_file_path = True
            super().setWindowFilePath(path)

    def writeSettings(self):
        settings = QtCore.QSettings()

        settings.setValue('geometry', self.saveGeometry())
        settings.setValue('state', self.saveState())

        settings.beginGroup('view_settings')
        settings.setValue('z_near', self.viewer.z_near)
        settings.setValue('z_far', self.viewer.z_far)
        settings.setValue('fov', self.viewer.fov)
        settings.setValue('movement_speed', self.viewer.movement_speed)
        settings.setValue('rotation_speed', self.viewer.rotation_speed)
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
        self.viewer.z_near = settings.value('z_near', 25, float)
        self.viewer.z_far = settings.value('z_far', 12800, float)
        self.viewer.fov = settings.value('fov', 22.5, float)
        self.viewer.movement_speed = settings.value('movement_speed', 10, float)
        self.viewer.rotation_speed = settings.value('rotation_speed', 1, float)
        settings.endGroup()

    def warning(self, message):
        QtWidgets.QMessageBox.warning(self, QtWidgets.qApp.applicationName(), message)

    def warning_file_open_failed(self, error):
        self.warning('Could not open file \'{}\': {}'.format(error.filename, error.strerror))

    def loadModel(self, file_name):
        with open(file_name, 'rb') as stream:
            model = j3d.model.unpack(stream)

        self.undo_stack.clear()
        self.preview.clear()
        self.material_form.clear()
        self.texture_form.clear()

        self.viewer.makeCurrent()
        if self.model is not None:
            self.model.gl_delete()
        self.model = views.model.Model(model)
        self.model.gl_init()

        self.viewer.setModel(self.model)
        self.explorer.setModel(self.model)

        self.action_open_animation.setEnabled(True)
        self.action_save_model.setEnabled(True)
        self.action_save_model_as.setEnabled(True)

        self.setWindowFilePath(file_name)

    def saveModel(self, file_name):
        with open(file_name, 'wb') as stream:
            #TODO: What if the file extension isn't .bmd/.bdl?
            j3d.model.pack(stream, self.model.viewed_object, os.path.splitext(file_name)[1].lower())

        self.undo_stack.setClean()
        self.setWindowFilePath(file_name)

    def loadAnimation(self, file_name):
        with open(file_name, 'rb') as stream:
            animation = j3d.animation.unpack(stream)

        self.viewer.setAnimation(animation)

    def importTexture(self, file_name):
        with open(file_name, 'rb') as stream:
            texture = gx.bti.unpack(stream)
        texture.name = os.path.splitext(os.path.basename(file_name))[0]
        return texture

    def exportTexture(self, file_name, texture):
        with open(file_name, 'wb') as stream:
            gx.bti.pack(stream, texture)

    def openFile(self, file_name):
        try:
            self.loadModel(file_name)
        except FILE_OPEN_ERRORS as error:
            self.warning_file_open_failed(error)

    def closeEvent(self, event):
        #self.writeSettings()
        super().closeEvent(event)

    @QtCore.pyqtSlot(bool)
    def on_undo_stack_cleanChanged(self, clean):
        self.setWindowModified(not clean)

    def on_explorer_currentMaterialChanged(self, material_index):
        self.material_form.setMaterial(self.model, material_index)
        self.dock_material_form.raise_()

    def on_explorer_currentTextureChanged(self, texture_index):
        self.preview.setTexture(self.model, texture_index)
        self.texture_form.setTexture(self.model, texture_index)
        self.dock_texture_form.raise_()

    @QtCore.pyqtSlot(QtCore.QPoint)
    def on_explorer_customContextMenuRequested(self, position):
        item = self.explorer.itemAt(position)
        if isinstance(item, widgets.explorer_widget.TextureItem):
            menu = QtWidgets.QMenu(self)
            menu.addAction(self.action_texture_export)
            menu.addAction(self.action_texture_replace)
            menu.exec_(self.explorer.mapToGlobal(position))

    @QtCore.pyqtSlot()
    def on_action_open_model_triggered(self):
        file_name, _ = QtWidgets.QFileDialog.getOpenFileName(
                self,
                'Open Model',
                self.windowFilePath(),
                'Nintendo J3D model (*.bmd *.bdl);;All files (*)')
        if not file_name: return

        try:
            self.loadModel(file_name)
        except FILE_OPEN_ERRORS as error:
            self.warning_file_open_failed(error)

    @QtCore.pyqtSlot()
    def on_action_open_animation_triggered(self):
        file_name, _ = QtWidgets.QFileDialog.getOpenFileName(
                self,
                'Open Animation',
                os.path.dirname(self.windowFilePath()),
                'Nintendo J3D animation (*.bck *.btk *.btp *.bva *.brk *.bpk);;All files (*)')
        if not file_name: return

        try:
            self.loadAnimation(file_name)
        except FILE_OPEN_ERRORS as error:
            self.warning_file_open_failed(error)
        except j3d.animation.IncompatibleAnimationError:
            self.warning('Incompatible animation')

    @QtCore.pyqtSlot()
    def on_action_save_model_triggered(self):
        try:
            self.saveModel(self.windowFilePath())
        except FILE_OPEN_ERRORS as error:
            self.warning_file_open_failed(error)

    @QtCore.pyqtSlot()
    def on_action_save_model_as_triggered(self):
        file_name, _ = QtWidgets.QFileDialog.getSaveFileName(
                self,
                'Save Model',
                self.windowFilePath(),
                'Nintendo J3D model (*.bmd *.bdl);;All files (*)')
        if not file_name: return

        try:
            self.saveModel(file_name)
        except FILE_OPEN_ERRORS as error:
            self.warning_file_open_failed(error)

    @QtCore.pyqtSlot()
    def on_action_texture_export_triggered(self):
        texture = self.model.viewed_object.textures[self.explorer.current_texture_index]
        file_name, _ = QtWidgets.QFileDialog.getSaveFileName(
                self,
                'Export Texture',
                os.path.join(os.path.dirname(self.windowFilePath()), texture.name + '.bti'),
                'BTI texture (*.bti);;All files (*)')
        if not file_name: return

        try:
            self.exportTexture(file_name, texture)
        except FILE_OPEN_ERRORS as error:
            self.warning_file_open_failed(error)

    @QtCore.pyqtSlot()
    def on_action_texture_replace_triggered(self):
        file_name, _ = QtWidgets.QFileDialog.getOpenFileName(
                self,
                'Open Texture',
                os.path.dirname(self.windowFilePath()),
                'BTI texture (*.bti);;All files (*)')
        if not file_name: return

        try:
            texture = self.importTexture(file_name)
        except FILE_OPEN_ERRORS as error:
            self.warning_file_open_failed(error)

        index = self.explorer.current_texture_index
        self.undo_stack.push(ReplaceTextureCommand(self.model, index, texture))

