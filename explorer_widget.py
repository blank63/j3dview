from PyQt4 import QtCore,QtGui
import qt
import gx


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


class TextureItem(QtGui.QTreeWidgetItem):

    def __init__(self,texture):
        super().__init__([texture.name])
        self.texture = texture
        self.texture.name_changed.connect(self.on_texture_name_changed)

    @QtCore.pyqtSlot(str)
    def on_texture_name_changed(self,name):
        self.setText(0,name)


class ExplorerWidget(QtGui.QTreeWidget):

    currentTextureChanged = QtCore.pyqtSignal(object)

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.header().close()
        self.currentItemChanged.connect(self.on_currentItemChanged)

        self.texture_list = QtGui.QTreeWidgetItem(['Textures'])
        self.addTopLevelItem(self.texture_list)

    def setModel(self,model):
        self.texture_list.takeChildren()
        for texture in model.textures:
            self.texture_list.addChild(TextureItem(TextureWrapper(texture)))

    @QtCore.pyqtSlot(QtGui.QTreeWidgetItem,QtGui.QTreeWidgetItem)
    def on_currentItemChanged(self,current,previous):
        if isinstance(current,TextureItem):
            self.currentTextureChanged.emit(current.texture)

