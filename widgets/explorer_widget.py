from enum import Enum
import os
from PyQt5.QtCore import Qt
from PyQt5 import QtCore, QtWidgets
from modelview.path import Path, PATH_BUILDER as _p
import models.material
import models.texture
from widgets.modelview import TreeView
from widgets.item_model_adaptor import (
    Entry,
    Item,
    AbstractListItem,
    ItemModelAdaptor
)


PathRole = Qt.UserRole + 1


class ListItem(AbstractListItem):

    def __init__(self, label, list_path):
        super().__init__([Entry(
            data=label,
            role_data={PathRole: list_path},
            drop_enabled=True
        )])
        self.list_path = list_path

    def create_child(self, index):
        child_path = self.list_path + _p[index]
        return Item([Entry(
            path=child_path + _p.name,
            role_data={PathRole: child_path},
            drag_enabled=True
        )])


class ModelAdaptor(ItemModelAdaptor):

    MIME_TYPE = 'application/x-modelview-path'

    rowDropped = QtCore.pyqtSignal(QtCore.QModelIndex, int)

    def __init__(self):
        super().__init__(column_count=1)
        self.material_list = ListItem('Materials', +_p.materials)
        self.add_top_level_item(self.material_list)
        self.texture_list = ListItem('Textures', +_p.textures)
        self.add_top_level_item(self.texture_list)

    def get_material_index(self, row):
        item = self.material_list.get_child(row)
        return self.get_item_index(item)

    def get_texture_index(self, row):
        item = self.texture_list.get_child(row)
        return self.get_item_index(item)

    def move_material(self, from_index, to_index):
        material = self.object_model.materials[from_index]
        self.undo_stack.beginMacro(f"Move material '{material.name}'")
        self.undo_stack.push(RemoveItemCommand(self.object_model.materials, from_index))
        self.undo_stack.push(InsertItemCommand(self.object_model.materials, to_index, material))
        self.undo_stack.endMacro()

    def move_texture(self, from_index, to_index):
        texture = self.object_model.textures[from_index]
        self.undo_stack.beginMacro(f"Move texture '{texture.name}'")
        self.undo_stack.push(RemoveItemCommand(self.object_model.textures, from_index))
        self.undo_stack.push(InsertItemCommand(self.object_model.textures, to_index, texture))
        self.undo_stack.endMacro()

    def supportedDropActions(self):
        return Qt.MoveAction

    def mimeTypes(self):
        return [self.MIME_TYPE]

    def mimeData(self, indexes):
        assert len(indexes) == 1
        index, = indexes
        path = index.data(PathRole)
        mime_data = QtCore.QMimeData()
        mime_data.setData(self.MIME_TYPE, str(path).encode())
        return mime_data

    def canDropMimeData(self, mime_data, action, row, column, parent):
        if not action == Qt.MoveAction:
            return False
        if not mime_data.hasFormat(self.MIME_TYPE):
            return False
        data = mime_data.data(self.MIME_TYPE).data()
        path = Path.from_string(data.decode())
        if path.match(+_p.materials[...]):
            return parent == self.get_item_index(self.material_list)
        if path.match(+_p.textures[...]):
            return parent == self.get_item_index(self.texture_list)
        return False

    def dropMimeData(self, mime_data, action, row, column, parent):
        if not self.canDropMimeData(mime_data, action, row, column, parent):
            return False
        data = mime_data.data(self.MIME_TYPE).data()
        path = Path.from_string(data.decode())
        from_index = path[-1].key
        if row < from_index:
            to_index = row
        else:
            # Account for the row being moved out from under where it is moved to
            to_index = row - 1
        if path.match(+_p.materials[...]):
            self.move_material(from_index, to_index)
        elif path.match(+_p.textures[...]):
            self.move_texture(from_index, to_index)
        self.rowDropped.emit(parent, to_index)
        return True


class InsertItemCommand(QtWidgets.QUndoCommand):

    def __init__(self, object_model, index, item):
        super().__init__()
        self.object_model = object_model
        self.index = index
        self.item = item

    def redo(self):
        self.object_model.insert(self.index, self.item)

    def undo(self):
        del self.object_model[self.index]


class RemoveItemCommand(QtWidgets.QUndoCommand):

    def __init__(self, object_model, index):
        super().__init__()
        self.object_model = object_model
        self.index = index
        self.item = object_model[index]

    def redo(self):
        del self.object_model[self.index]

    def undo(self):
        self.object_model.insert(self.index, self.item)


class ExplorerWidget(QtWidgets.QWidget):

    currentMaterialChanged = QtCore.pyqtSignal(models.material.Material)
    currentTextureChanged = QtCore.pyqtSignal(models.texture.Texture)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.model = None
        self.undo_stack = None

        self.model_adaptor = ModelAdaptor()
        self.model_adaptor.rowDropped.connect(self.on_rowDropped)
        self.tree_view = TreeView()
        self.tree_view.setHeaderHidden(True)
        self.tree_view.setDragEnabled(True)
        self.tree_view.setDragDropMode(QtWidgets.QTreeView.InternalMove)
        self.tree_view.setModel(self.model_adaptor)
        self.tree_view.selectionModel().currentRowChanged.connect(self.on_currentRowChanged)

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.tree_view)
        self.setLayout(layout)

        self.action_import = QtWidgets.QAction('Import...')
        self.action_import.triggered.connect(self.on_action_import_triggered)
        self.addAction(self.action_import)
        self.action_export = QtWidgets.QAction('Export...')
        self.action_export.triggered.connect(self.on_action_export_triggered)
        self.addAction(self.action_export)
        self.action_remove = QtWidgets.QAction('Remove')
        self.action_remove.triggered.connect(self.on_action_remove_triggered)
        self.addAction(self.action_remove)

    def setUndoStack(self, undo_stack):
        self.undo_stack = undo_stack
        self.model_adaptor.setUndoStack(undo_stack)

    def setModel(self, model):
        self.model = model
        self.model_adaptor.setObjectModel(model)

    def setCurrentMaterial(self, material_index):
        index = self.model_adaptor.get_material_index(material_index)
        self.tree_view.setCurrentIndex(index)

    def setCurrentTexture(self, texture_index):
        index = self.model_adaptor.get_texture_index(texture_index)
        self.tree_view.setCurrentIndex(index)

    def import_materials(self):
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            caption='Import Materials',
            directory=os.path.dirname(self.model.file_path),
            filter='BMT material archive (*.bmt);;All files (*)'
        )
        if not file_path:
            return
        try:
            material_archive = models.material.MaterialArchive.load(file_path)
        except (FileNotFoundError, IsADirectoryError, PermissionError) as error:
            message = QtWidgets.QMessageBox()
            message.setIcon(QtWidgets.QMessageBox.Warning)
            message.setText(f"Could not open file '{error.filename}'")
            message.setInformativeText(error.strerror)
            message.exec_()
            return
        insert_index = len(self.model.materials)
        self.undo_stack.beginMacro('Import materials')
        for texture in material_archive.textures:
            self.append_texture(texture)
        for material in material_archive.materials:
            self.append_material(material)
        self.undo_stack.endMacro()
        self.setCurrentMaterial(insert_index)

    def export_material(self, index):
        material = self.model.materials[index]
        material_archive = models.material.MaterialArchive([material])
        directory_path = os.path.dirname(self.model.file_path)
        file_name = material.name + '.bmt'
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            caption='Export Material',
            directory=os.path.join(directory_path, file_name),
            filter='BMT material archive (*.bmt);;All files (*)'
        )
        if not file_path:
            return
        try:
            material_archive.save(file_path)
        except (FileNotFoundError, IsADirectoryError, PermissionError) as error:
            message = QtWidgets.QMessageBox()
            message.setIcon(QtWidgets.QMessageBox.Warning)
            message.setText(f"Could not open file '{error.filename}'")
            message.setInformativeText(error.strerror)
            message.exec_()
            return

    def append_material(self, material):
        index = len(self.model.materials)
        command = InsertItemCommand(self.model.materials, index, material)
        command.setText(f"Insert material '{material.name}'")
        self.undo_stack.push(command)

    def remove_material(self, index):
        material = self.model.materials[index]
        nodes = self.model.get_nodes_using_material(index)
        if nodes:
            message = QtWidgets.QMessageBox()
            message.setIcon(QtWidgets.QMessageBox.Warning)
            message.setText(f'Material {material.name} is being used and cannot be removed.')
            message.setInformativeText(f'Used by {len(nodes)} scene graph node(s).')
            message.exec_()
            return
        command = RemoveItemCommand(self.model.materials, index)
        command.setText(f"Remove material '{material.name}'")
        self.undo_stack.push(command)

    def import_texture(self):
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            caption='Import Texture',
            directory=os.path.dirname(self.model.file_path),
            filter='BTI texture (*.bti);;All files (*)'
        )
        if not file_path:
            return
        try:
            texture = models.texture.Texture.load(file_path)
        except (FileNotFoundError, IsADirectoryError, PermissionError) as error:
            message = QtWidgets.QMessageBox()
            message.setIcon(QtWidgets.QMessageBox.Warning)
            message.setText(f"Could not open file '{error.filename}'")
            message.setInformativeText(error.strerror)
            message.exec_()
            return
        self.append_texture(texture)
        self.setCurrentTexture(len(self.model.textures) - 1)

    def export_texture(self, index):
        texture = self.model.textures[index]
        directory_path = os.path.dirname(self.model.file_path)
        file_name = texture.name + '.bti'
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            caption='Export Texture',
            directory=os.path.join(directory_path, file_name),
            filter='BTI texture (*.bti);;All files (*)'
        )
        if not file_path:
            return
        try:
            texture.save(file_path)
        except (FileNotFoundError, IsADirectoryError, PermissionError) as error:
            message = QtWidgets.QMessageBox()
            message.setIcon(QtWidgets.QMessageBox.Warning)
            message.setText(f"Could not open file '{error.filename}'")
            message.setInformativeText(error.strerror)
            message.exec_()
            return

    def append_texture(self, texture):
        index = len(self.model.textures)
        command = InsertItemCommand(self.model.textures, index, texture)
        command.setText(f"Insert texture '{texture.name}'")
        self.undo_stack.push(command)

    def remove_texture(self, index):
        texture = self.model.textures[index]
        materials = self.model.get_materials_using_texture(index)
        if materials:
            message = QtWidgets.QMessageBox()
            message.setIcon(QtWidgets.QMessageBox.Warning)
            message.setText(f'Texture {texture.name} is being used and cannot be removed.')
            message.setInformativeText(
                f'Used by the following material(s):\n' +
                '\n'.join(material.name for material in materials)
            )
            message.exec_()
            return
        command = RemoveItemCommand(self.model.textures, index)
        command.setText(f"Remove texture '{texture.name}'")
        self.undo_stack.push(command)

    def contextMenuEvent(self, event):
        index = self.tree_view.indexAt(event.pos())
        path = index.data(PathRole)
        if path is None:
            return
        if path in {+_p.materials, +_p.textures}:
            menu = QtWidgets.QMenu(self)
            menu.addAction(self.action_import)
            menu.exec_(self.mapToGlobal(event.pos()))
        elif path.match(+_p.materials[...]) or path.match(+_p.textures[...]):
            menu = QtWidgets.QMenu(self)
            menu.addAction(self.action_import)
            menu.addAction(self.action_export)
            menu.addAction(self.action_remove)
            menu.exec_(self.mapToGlobal(event.pos()))
        super().contextMenuEvent(event)

    @QtCore.pyqtSlot(QtCore.QModelIndex, QtCore.QModelIndex)
    def on_currentRowChanged(self, current, previous):
        path = current.data(PathRole)
        if path is None:
            return
        if path.match(+_p.materials[...]):
            material = path.get_value(self.model)
            self.currentMaterialChanged.emit(material)
        elif path.match(+_p.textures[...]):
            texture = path.get_value(self.model)
            self.currentTextureChanged.emit(texture)

    @QtCore.pyqtSlot(QtCore.QModelIndex, int)
    def on_rowDropped(self, parent, row):
        index = self.model_adaptor.index(row, 0, parent)
        self.tree_view.setCurrentIndex(index)

    @QtCore.pyqtSlot()
    def on_action_import_triggered(self):
        index = self.tree_view.currentIndex()
        path = index.data(PathRole)
        if path is None:
            return
        if path == +_p.materials or path.match(+_p.materials[...]):
            self.import_materials()
        elif path == +_p.textures or path.match(+_p.textures[...]):
            self.import_texture()

    @QtCore.pyqtSlot()
    def on_action_export_triggered(self):
        index = self.tree_view.currentIndex()
        path = index.data(PathRole)
        if path is None:
            return
        if path.match(+_p.materials[...]):
            index = path[-1].key
            self.export_material(index)
        elif path.match(+_p.textures[...]):
            index = path[-1].key
            self.export_texture(index)

    @QtCore.pyqtSlot()
    def on_action_remove_triggered(self):
        index = self.tree_view.currentIndex()
        path = index.data(PathRole)
        if path is None:
            return
        if path.match(+_p.materials[...]):
            index = path[-1].key
            self.remove_material(index)
        elif path.match(+_p.textures[...]):
            index = path[-1].key
            self.remove_texture(index)

