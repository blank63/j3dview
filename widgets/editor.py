import io
import pkgutil
import os.path
from PyQt5.QtCore import Qt
from PyQt5 import QtCore, QtWidgets, QtGui, uic
import j3d.animation
import models.model
from widgets.modelview import UndoStack
from widgets.info_dialog import InfoDialog
from widgets.scene_graph_dialog import SceneGraphDialog
from widgets.advanced_material_dialog import AdvancedMaterialDialog


FILE_OPEN_ERRORS = (FileNotFoundError, IsADirectoryError, PermissionError)


class Editor(QtWidgets.QMainWindow):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.undo_stack = UndoStack(self, objectName='undo_stack')
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
        self.action_undo.setShortcutContext(Qt.ApplicationShortcut)
        self.action_redo.setShortcut(QtGui.QKeySequence.Redo)
        self.action_redo.setShortcutContext(Qt.ApplicationShortcut)

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
        self.explorer.setUndoStack(self.undo_stack)
        self.material_form.setUndoStack(self.undo_stack)
        self.texture_form.setUndoStack(self.undo_stack)
        self.tabifyDockWidget(self.dock_model_form, self.dock_material_form)
        self.tabifyDockWidget(self.dock_material_form, self.dock_texture_form)
        self.dock_model_form.raise_()

        self.info_dialog = None
        self.model_form.info_button.clicked.connect(self.on_model_form_info_button_clicked)
        self.scene_graph_dialog = None
        self.model_form.scene_graph_button.clicked.connect(self.on_model_form_scene_graph_button_clicked)
        self.advanced_material_dialog = None
        self.material_form.advanced_button.clicked.connect(self.on_material_form_advanced_button_clicked)

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

    def loadModel(self, file_path):
        model = models.model.Model.load(file_path)

        self.undo_stack.clear()
        self.preview.clear()
        self.model_form.clear()
        self.material_form.clear()
        self.texture_form.clear()
        if self.info_dialog is not None:
            self.info_dialog.clear()
        if self.scene_graph_dialog is not None:
            self.scene_graph_dialog.clear()
        if self.advanced_material_dialog is not None:
            self.advanced_material_dialog.clear()

        self.viewer.makeCurrent()
        if self.model is not None:
            self.model.gl_delete()
        self.model = model
        self.model.gl_init()

        self.viewer.setModel(self.model)
        self.explorer.setModel(self.model)
        self.model_form.setModel(self.model)
        self.material_form.setTextures(self.model.textures)
        if self.info_dialog is not None:
            self.info_dialog.setModel(model)
        if self.scene_graph_dialog is not None:
            self.scene_graph_dialog.setModel(model)

        self.action_open_animation.setEnabled(True)
        self.action_save_model.setEnabled(True)
        self.action_save_model_as.setEnabled(True)

        self.setWindowFilePath(file_path)

    def saveModel(self, file_path):
        self.model.save(file_path)
        self.undo_stack.setClean()
        self.setWindowFilePath(file_path)

    def loadAnimation(self, file_name):
        with open(file_name, 'rb') as stream:
            animation = j3d.animation.unpack(stream)

        self.viewer.setAnimation(animation)

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

    def on_explorer_currentMaterialChanged(self, material):
        self.material_form.setMaterial(material)
        self.dock_material_form.raise_()
        if self.advanced_material_dialog is not None:
            self.advanced_material_dialog.setMaterial(material)

    def on_explorer_currentTextureChanged(self, texture):
        self.preview.setTexture(texture)
        self.texture_form.setTexture(texture)
        self.dock_texture_form.raise_()

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

        extension = os.path.splitext(file_name)[1].lower()
        if extension == '.bmd':
            self.model.file_type = b'bmd3'
        elif extension == '.bdl':
            self.model.file_type = b'bdl4'
        else:
            #TODO: What if the file extension isn't .bmd/.bdl?
            pass

        try:
            self.saveModel(file_name)
        except FILE_OPEN_ERRORS as error:
            self.warning_file_open_failed(error)

    @QtCore.pyqtSlot(bool)
    def on_model_form_info_button_clicked(self, checked):
        if self.info_dialog is not None:
            return
        self.info_dialog = InfoDialog()
        self.info_dialog.finished.connect(self.on_info_dialog_finished)
        self.info_dialog.setModel(self.model)
        self.info_dialog.show()
        self.info_dialog.raise_()
        self.info_dialog.activateWindow()

    @QtCore.pyqtSlot(int)
    def on_info_dialog_finished(self, result):
        self.info_dialog.finished.disconnect(self.on_info_dialog_finished)
        self.info_dialog = None

    @QtCore.pyqtSlot(bool)
    def on_model_form_scene_graph_button_clicked(self, checked):
        if self.scene_graph_dialog is not None:
            return
        self.scene_graph_dialog = SceneGraphDialog()
        self.scene_graph_dialog.setUndoStack(self.undo_stack)
        self.scene_graph_dialog.finished.connect(self.on_scene_graph_dialog_finished)
        self.scene_graph_dialog.setModel(self.model)
        self.scene_graph_dialog.show()
        self.scene_graph_dialog.raise_()
        self.scene_graph_dialog.activateWindow()

    @QtCore.pyqtSlot(int)
    def on_scene_graph_dialog_finished(self, result):
        self.scene_graph_dialog.finished.disconnect(self.on_scene_graph_dialog_finished)
        self.scene_graph_dialog.clear()
        self.scene_graph_dialog = None

    @QtCore.pyqtSlot(bool)
    def on_material_form_advanced_button_clicked(self, checked):
        if self.advanced_material_dialog is not None:
            return
        self.advanced_material_dialog = AdvancedMaterialDialog()
        self.advanced_material_dialog.setUndoStack(self.undo_stack)
        self.advanced_material_dialog.finished.connect(self.on_advanced_material_dialog_finished)
        self.advanced_material_dialog.setMaterial(self.material_form.material)
        self.advanced_material_dialog.show()
        self.advanced_material_dialog.raise_()
        self.advanced_material_dialog.activateWindow()

    @QtCore.pyqtSlot(int)
    def on_advanced_material_dialog_finished(self, result):
        self.advanced_material_dialog.finished.disconnect(self.on_advanced_material_dialog_finished)
        self.advanced_material_dialog.clear()
        self.advanced_material_dialog = None

    @QtCore.pyqtSlot()
    def on_action_quit_triggered(self):
        QtWidgets.qApp.exit()

