from PyQt5 import QtCore, QtWidgets


class TextureItem(QtWidgets.QTreeWidgetItem):

    def __init__(self, texture):
        super().__init__()
        self.texture = None
        self.setTexture(texture)

    def setTexture(self, texture):
        if self.texture is not None:
            self.texture.unregister(self.reload)
        self.texture = texture
        self.reload()
        self.texture.register(self.reload)

    def reload(self):
        self.setText(0, self.texture.name)


class ExplorerWidget(QtWidgets.QTreeWidget):

    currentTextureChanged = QtCore.pyqtSignal(object)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.header().close()
        self.model = None
        self.texture_list = QtWidgets.QTreeWidgetItem(['Textures'])
        self.addTopLevelItem(self.texture_list)
        self.currentItemChanged.connect(self.on_currentItemChanged)

    def setModel(self,model):
        self.model = model
        self.texture_list.takeChildren()
        self.texture_list.addChildren([TextureItem(texture) for texture in self.model.textures])

    @QtCore.pyqtSlot(QtWidgets.QTreeWidgetItem,QtWidgets.QTreeWidgetItem)
    def on_currentItemChanged(self,current,previous):
        if isinstance(current, TextureItem):
            self.currentTextureChanged.emit(current.texture)

