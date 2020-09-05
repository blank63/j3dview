from PyQt5 import QtCore, QtWidgets
import views.model


class MaterialItem(QtWidgets.QTreeWidgetItem):

    def __init__(self, material):
        super().__init__()
        self.material = None
        self.setMaterial(material)

    def setMaterial(self, material):
        if self.material is not None:
            self.material.unregister_listener(self)
        self.material = material
        self.reload()
        self.material.register_listener(self)

    def receive_event(self, sender, event):
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
            self.texture.unregister_listener(self)
        self.texture = texture
        self.reload()
        self.texture.register_listener(self)

    def receive_event(self, sender, event):
        self.reload()

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
        if self.model is not None:
            self.model.unregister_listener(self)
        self.model = model
        self.setCurrentItem(None)
        self.reload_materials()
        self.reload_textures()
        self.model.register_listener(self)

    def receive_event(self, sender, event):
        if isinstance(event, views.model.TexturesChangedEvent):
            self.reload_textures()

    def reload_materials(self):
        self.material_list.takeChildren()
        self.material_list.addChildren([
            MaterialItem(material)
            for material in self.model.materials
        ])

    def reload_textures(self):
        index = self.current_texture_index
        self.texture_list.takeChildren()
        self.texture_list.addChildren([
            TextureItem(texture)
            for texture in self.model.textures
        ])
        if index != -1:
            self.setCurrentItem(self.texture_list.child(index))

    @property
    def current_texture_index(self):
        return self.texture_list.indexOfChild(self.currentItem())

    @QtCore.pyqtSlot(QtWidgets.QTreeWidgetItem, QtWidgets.QTreeWidgetItem)
    def on_currentItemChanged(self, current, previous):
        if isinstance(current, MaterialItem):
            self.currentMaterialChanged.emit(current.material)
        if isinstance(current, TextureItem):
            self.currentTextureChanged.emit(current.texture)

