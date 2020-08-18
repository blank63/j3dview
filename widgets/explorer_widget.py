from PyQt5 import QtCore, QtWidgets


class MaterialItem(QtWidgets.QTreeWidgetItem):

    def __init__(self, material):
        super().__init__()
        self.material = None
        self.setMaterial(material)

    def setMaterial(self, material):
        self.material = material
        self.reload()

    def reload(self):
        self.setText(0, self.material.name)


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

    currentMaterialChanged = QtCore.pyqtSignal(object)
    currentTextureChanged = QtCore.pyqtSignal(object)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.header().close()
        self.model = None
        self.material_list = QtWidgets.QTreeWidgetItem(['Materials'])
        self.texture_list = QtWidgets.QTreeWidgetItem(['Textures'])
        self.addTopLevelItems([
            self.material_list,
            self.texture_list
        ])
        self.currentItemChanged.connect(self.on_currentItemChanged)

    def setModel(self, model):
        self.model = model
        self.material_list.takeChildren()
        self.material_list.addChildren([
            MaterialItem(material)
            for material in model.materials
        ])
        self.texture_list.takeChildren()
        self.texture_list.addChildren([
            TextureItem(texture)
            for texture in model.textures
        ])

    @property
    def current_texture_index(self):
        return self.texture_list.indexOfChild(self.currentItem())

    @QtCore.pyqtSlot(QtWidgets.QTreeWidgetItem, QtWidgets.QTreeWidgetItem)
    def on_currentItemChanged(self, current, previous):
        if isinstance(current, MaterialItem):
            self.currentMaterialChanged.emit(current.material)
        if isinstance(current, TextureItem):
            self.currentTextureChanged.emit(current.texture)

