import io
import pkgutil
import os.path
from PyQt5 import QtCore,QtWidgets,QtGui,uic
import qt
import gx
import gx.bti
import j3d.model
import j3d.animation
import widgets.explorer_widget


FILE_OPEN_ERRORS = (FileNotFoundError,IsADirectoryError,PermissionError)


class TextureWrapper(qt.Wrapper):
    name = qt.Wrapper.Property(str)
    wrap_s = qt.Wrapper.Property(gx.WrapMode)
    wrap_t = qt.Wrapper.Property(gx.WrapMode)
    minification_filter = qt.Wrapper.Property(gx.FilterMode)
    magnification_filter = qt.Wrapper.Property(gx.FilterMode)
    minimum_lod = qt.Wrapper.Property(float)
    maximum_lod = qt.Wrapper.Property(float)
    lod_bias = qt.Wrapper.Property(float)
    unknown0 = qt.Wrapper.Property(int)
    unknown1 = qt.Wrapper.Property(int)
    unknown2 = qt.Wrapper.Property(int)

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)

        self.wrap_s_changed.connect(self.on_wrap_s_changed)
        self.wrap_t_changed.connect(self.on_wrap_t_changed)
        self.minification_filter_changed.connect(self.on_minification_filter_changed)
        self.magnification_filter_changed.connect(self.on_magnification_filter_changed)
        self.minimum_lod_changed.connect(self.on_minimum_lod_changed)
        self.maximum_lod_changed.connect(self.on_maximum_lod_changed)
        self.lod_bias_changed.connect(self.on_lod_bias_changed)

    @QtCore.pyqtSlot(gx.WrapMode)
    def on_wrap_s_changed(self,value):
        self.wrapped_object.gl_wrap_s_need_update = True

    @QtCore.pyqtSlot(gx.WrapMode)
    def on_wrap_t_changed(self,value):
        self.wrapped_object.gl_wrap_t_need_update = True

    @QtCore.pyqtSlot(gx.FilterMode)
    def on_minification_filter_changed(self,value):
        self.wrapped_object.gl_minification_filter_need_update = True

    @QtCore.pyqtSlot(gx.FilterMode)
    def on_magnification_filter_changed(self,value):
        self.wrapped_object.gl_magnification_filter_need_update = True

    @QtCore.pyqtSlot(float)
    def on_minimum_lod_changed(self,value):
        self.wrapped_object.gl_minimum_lod_need_update = True

    @QtCore.pyqtSlot(float)
    def on_maximum_lod_changed(self,value):
        self.wrapped_object.gl_maximum_lod_need_update = True

    @QtCore.pyqtSlot(float)
    def on_lod_bias_changed(self,value):
        self.wrapped_object.gl_lod_bias_need_update = True


class TextureListWrapper(QtCore.QObject):

    entry_changed = QtCore.pyqtSignal(int,object)

    def __init__(self,textures,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.textures = textures
        self.wrapped_textures = [TextureWrapper(texture) for texture in textures]

    def __setitem__(self,key,value):
        self.textures[key] = value.wrapped_object
        self.wrapped_textures[key] = value
        self.entry_changed.emit(key,value)

    def __getitem__(self,key):
        return self.wrapped_textures[key]

    def __len__(self):
        return len(self.wrapped_textures)

    def __iter__(self):
        yield from self.wrapped_textures


class ModelWrapper(qt.Wrapper):

    def __init__(self,model,*args,**kwargs):
        super().__init__(model,*args,**kwargs)
        self.textures = TextureListWrapper(model.textures)


class TextureReplaceCommand(QtWidgets.QUndoCommand):
    #TODO: Should something be done about textures that are no longer being
    # used, but are still in the undo stack?

    def __init__(self,textures,index,new_value):
        super().__init__('Replace Texture')
        self.textures = textures
        self.index = index
        self.old_value = textures[index]
        self.new_value = new_value

    def redo(self):
        self.textures[self.index] = self.new_value

    def undo(self):
        self.textures[self.index] = self.old_value


class Editor(QtWidgets.QMainWindow):

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)

        self.undo_stack = QtWidgets.QUndoStack(self,objectName='undo_stack')
        self.action_undo = self.undo_stack.createUndoAction(self)
        self.action_redo = self.undo_stack.createRedoAction(self)

        self.ui = uic.loadUi(io.BytesIO(pkgutil.get_data(__package__,'Editor.ui')),self)

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

        #XXX It appears that actions have to be manually added to the widget
        # for shortcuts to work. Possibly a bug?
        self.addAction(self.action_open_model)
        self.addAction(self.action_save_model)
        self.addAction(self.action_save_model_as)
        self.addAction(self.action_quit)
        self.addAction(self.action_undo)
        self.addAction(self.action_redo)

        self.view_settings.setViewer(self.viewer)
        self.dock_view_settings.hide()

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

    def warning(self,message):
        QtWidgets.QMessageBox.warning(self,QtWidgets.qApp.applicationName(),message)

    def warning_file_open_failed(self,error):
        self.warning('Could not open file \'{}\': {}'.format(error.filename,error.strerror))

    def loadModel(self,file_name):
        with open(file_name,'rb') as stream:
            model = j3d.model.unpack(stream)

        self.undo_stack.clear()

        self.model = ModelWrapper(model)
        self.viewer.setModel(self.model)
        self.explorer.setModel(self.model)

        self.action_open_animation.setEnabled(True)
        self.action_save_model.setEnabled(True)
        self.action_save_model_as.setEnabled(True)

        self.setWindowFilePath(file_name)

    def saveModel(self,file_name):
        with open(file_name,'wb') as stream:
            #TODO: What if the file extension isn't .bmd/.bdl?
            j3d.model.pack(stream,self.model,os.path.splitext(file_name)[1].lower())

        self.undo_stack.setClean()
        self.setWindowFilePath(file_name)

    def loadAnimation(self,file_name):
        with open(file_name,'rb') as stream:
            animation = j3d.animation.unpack(stream)

        self.viewer.setAnimation(animation)

    def importTexture(self,file_name):
        with open(file_name,'rb') as stream:
            texture = gx.bti.unpack(stream)

        texture.name = os.path.splitext(os.path.basename(file_name))[0]
        texture.gl_init() #TODO: This is not the right place to do this
        return TextureWrapper(texture)

    def exportTexture(self,file_name,texture):
        with open(file_name,'wb') as stream:
            gx.bti.pack(stream,texture)

    def openFile(self,file_name):
        try:
            self.loadModel(file_name)
        except FILE_OPEN_ERRORS as error:
            self.warning_file_open_failed(error)

    def closeEvent(self,event):
        #self.writeSettings()
        super().closeEvent(event)

    @QtCore.pyqtSlot(bool)
    def on_undo_stack_cleanChanged(self,clean):
        self.setWindowModified(not clean)

    def on_explorer_currentTextureChanged(self,texture):
        self.preview.setTexture(texture)
        self.texture.setTexture(texture)

    @QtCore.pyqtSlot(QtCore.QPoint)
    def on_explorer_customContextMenuRequested(self,position):
        item = self.explorer.itemAt(position)
        if isinstance(item,widgets.explorer_widget.TextureItem):
            menu = QtWidgets.QMenu(self)
            menu.addAction(self.action_texture_export)
            menu.addAction(self.action_texture_replace)
            menu.exec_(self.explorer.mapToGlobal(position))

    @QtCore.pyqtSlot()
    def on_action_open_model_triggered(self):
        file_name,_ = QtWidgets.QFileDialog.getOpenFileName(
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
        file_name,_ = QtWidgets.QFileDialog.getOpenFileName(
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
        file_name,_ = QtWidgets.QFileDialog.getSaveFileName(
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
        texture = self.explorer.currentItem().texture
        file_name = QtWidgets.QFileDialog.getSaveFileName(
                self,
                'Export Texture',
                os.path.join(os.path.dirname(self.windowFilePath()),texture.name + '.bti'),
                'BTI texture (*.bti);;All files (*)')
        if not file_name: return

        try:
            self.exportTexture(file_name,texture)
        except FILE_OPEN_ERRORS as error:
            self.warning_file_open_failed(error)

    @QtCore.pyqtSlot()
    def on_action_texture_replace_triggered(self):
        index = self.explorer.texture_list.indexOfChild(self.explorer.currentItem())
        file_name = QtWidgets.QFileDialog.getOpenFileName(
                self,
                'Open Texture',
                os.path.dirname(self.windowFilePath()),
                'BTI texture (*.bti);;All files (*)')
        if not file_name: return

        try:
            texture = self.importTexture(file_name)
            self.undo_stack.push(TextureReplaceCommand(self.model.textures,index,texture))
        except FILE_OPEN_ERRORS as error:
            self.warning_file_open_failed(error)
