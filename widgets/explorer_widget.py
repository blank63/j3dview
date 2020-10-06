from PyQt5 import QtCore, QtWidgets
import views
from views import path_builder as _p


class MaterialItem(QtWidgets.QTreeWidgetItem):
    pass


class TextureItem(QtWidgets.QTreeWidgetItem):
    pass


class ExplorerWidget(QtWidgets.QTreeWidget):

    currentMaterialChanged = QtCore.pyqtSignal(int)
    currentTextureChanged = QtCore.pyqtSignal(int)

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

    def handle_event(self, event, path):
        if isinstance(event, views.ValueChangedEvent):
            if path.match(+_p.materials[...].name):
                index = path[1].key
                material = self.model.materials[index]
                self.material_list.child(index).setText(0, material.name)
                return
            if path.match(+_p.textures[...].name):
                index = path[1].key
                texture = self.model.textures[index]
                self.texture_list.child(index).setText(0, texture.name)
                return
            if path.match(+_p.textures[...]):
                index = path[1].key
                texture = self.model.textures[index]
                self.texture_list.child(index).setText(0, texture.name)
                if self.texture_list.indexOfChild(self.currentItem()) == index:
                    self.currentTextureChanged.emit(index)
                return

    def reload_materials(self):
        self.material_list.takeChildren()
        self.material_list.addChildren([
            MaterialItem([material.name])
            for material in self.model.materials
        ])

    def reload_textures(self):
        self.texture_list.takeChildren()
        self.texture_list.addChildren([
            TextureItem([texture.name])
            for texture in self.model.textures
        ])

    @property
    def current_material_index(self):
        return self.material_list.indexOfChild(self.currentItem())

    @property
    def current_texture_index(self):
        return self.texture_list.indexOfChild(self.currentItem())

    @QtCore.pyqtSlot(QtWidgets.QTreeWidgetItem, QtWidgets.QTreeWidgetItem)
    def on_currentItemChanged(self, current, previous):
        if isinstance(current, MaterialItem):
            index = self.material_list.indexOfChild(current)
            self.currentMaterialChanged.emit(index)
        if isinstance(current, TextureItem):
            index = self.texture_list.indexOfChild(current)
            self.currentTextureChanged.emit(index)

