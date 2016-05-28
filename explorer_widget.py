from PyQt5 import QtCore,QtWidgets


class TextureItem(QtWidgets.QTreeWidgetItem):

    def __init__(self,texture):
        super().__init__()
        self.texture = None
        self.setTexture(texture)

    def setTexture(self,texture):
        if self.texture is not None:
            self.texture.name_changed.disconnect(self.on_texture_name_changed)

        self.setText(0,texture.name)
        self.texture = texture
        self.texture.name_changed.connect(self.on_texture_name_changed)

    @QtCore.pyqtSlot(str)
    def on_texture_name_changed(self,name):
        self.setText(0,name)


class ExplorerWidget(QtWidgets.QTreeWidget):

    currentTextureChanged = QtCore.pyqtSignal(object)

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.header().close()
        self.model = None
        self.texture_list = QtWidgets.QTreeWidgetItem(['Textures'])
        self.addTopLevelItem(self.texture_list)
        self.currentItemChanged.connect(self.on_currentItemChanged)

    def setModel(self,model):
        if self.model is not None:
            self.model.textures.entry_changed.disconnect(self.on_texture_changed)

        self.model = model

        self.texture_list.takeChildren()
        self.texture_list.addChildren([TextureItem(texture) for texture in self.model.textures])
        self.model.textures.entry_changed.connect(self.on_texture_changed)

    @QtCore.pyqtSlot(QtWidgets.QTreeWidgetItem,QtWidgets.QTreeWidgetItem)
    def on_currentItemChanged(self,current,previous):
        if isinstance(current,TextureItem):
            self.currentTextureChanged.emit(current.texture)

    @QtCore.pyqtSlot(int,object)
    def on_texture_changed(self,index,texture):
        item = self.texture_list.child(index)
        item.setTexture(texture)
        if item is self.currentItem():
            self.currentTextureChanged.emit(texture)

