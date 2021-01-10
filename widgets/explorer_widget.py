from enum import Enum
import os
from PyQt5 import QtCore, QtWidgets
import views
from views import path_builder as _p
import views.texture
from widgets.view_form import Item, GroupItem, ItemModelAdaptor


PathRole = QtCore.Qt.UserRole


class ElementItem(Item):

    def __init__(self, path):
        super().__init__()
        self.path = path
        self.triggers = frozenset((path + _p.name,))

    @property
    def column_count(self):
        return 1

    def get_flags(self, column):
        return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsDragEnabled

    def get_data(self, column, role):
        if role == QtCore.Qt.DisplayRole:
            return self.path.get_value(self.model.view).name
        if role == PathRole:
            return self.path
        return QtCore.QVariant()

    def handle_event(self, event, path):
        self.model.item_data_changed(self)


class ListItem(GroupItem):

    def __init__(self, label, path):
        super().__init__([label])
        self.path = path

    @property
    def view(self):
        return self.path.get_value(self.model.view)

    def get_flags(self, column):
        return super().get_flags(column) | QtCore.Qt.ItemIsDropEnabled

    def get_data(self, column, role):
        if role == PathRole:
            return self.path
        return super().get_data(column, role)

    def initialize(self):
        for i in range(len(self.view)):
            element = ElementItem(self.path + _p[i])
            self.model.add_item(element, self)

    def handle_event(self, event, path):
        index = self.model.get_item_index(self)
        row = path[-1].key
        if isinstance(event, views.CreateEvent):
            self.model.beginInsertRows(index, row, row)
            element_index = len(self.view) - 1
            element = ElementItem(self.path  + _p[element_index])
            self.model.add_item(element, self)
            self.model.endInsertRows()
        elif isinstance(event, views.DeleteEvent):
            self.model.beginRemoveRows(index, row, row)
            self.model.take_item(self.child_count - 1, self)
            self.model.endRemoveRows()


class ModelAdaptor(ItemModelAdaptor):

    MIME_TYPE = 'application/x-modelview-path'

    rowDropped = QtCore.pyqtSignal(QtCore.QModelIndex, int)

    def __init__(self, model, undo_stack):
        super().__init__(model)
        self.undo_stack = undo_stack
        self.set_header_labels(['Value'])
        self.material_list = ListItem('Materials', +_p.materials)
        self.add_item(self.material_list)
        self.material_list.initialize()
        self.texture_list = ListItem('Textures', +_p.textures)
        self.add_item(self.texture_list)
        self.texture_list.initialize()

    def get_texture_index(self, row):
        item = self.texture_list.get_child(row)
        return self.get_item_index(item)

    def supportedDropActions(self):
        return QtCore.Qt.MoveAction

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
        if not action == QtCore.Qt.MoveAction:
            return False
        if not mime_data.hasFormat(self.MIME_TYPE):
            return False
        data = mime_data.data(self.MIME_TYPE).data()
        path = views.Path.from_string(data.decode())
        if path.match(+_p.textures[...]):
            return parent == self.get_item_index(self.texture_list)
        return False

    def dropMimeData(self, mime_data, action, row, column, parent):
        if not self.canDropMimeData(mime_data, action, row, column, parent):
            return False
        data = mime_data.data(self.MIME_TYPE).data()
        path = views.Path.from_string(data.decode())
        from_index = path[-1].key
        if row < from_index:
            to_index = row
        else:
            # Account for the row being moved out from under where it is moved to
            to_index = row - 1
        texture = self.view.textures[from_index]
        self.undo_stack.beginMacro(f"Move texture '{texture.name}'")
        self.undo_stack.push(RemoveTextureCommand(self.view, from_index))
        self.undo_stack.push(InsertTextureCommand(self.view, to_index, texture))
        self.undo_stack.endMacro()
        self.rowDropped.emit(parent, to_index)
        return True

    def handle_event(self, event, path):
        if path.match(+_p.textures[...]):
            self.texture_list.handle_event(event, path)
        super().handle_event(event, path)


class InsertTextureCommand(QtWidgets.QUndoCommand):

    def __init__(self, model, index, texture):
        super().__init__()
        self.model = model
        self.index = index
        self.texture = texture
        self.setText(f"Insert texture '{self.texture.name}'")

    def redo(self):
        self.model.textures.insert(self.index, self.texture)

    def undo(self):
        del self.model.textures[self.index]


class RemoveTextureCommand(QtWidgets.QUndoCommand):

    def __init__(self, model, index):
        super().__init__()
        self.model = model
        self.index = index
        self.texture = model.textures[index]
        self.setText(f"Remove texture '{self.texture.name}'")

    def redo(self):
        del self.model.textures[self.index]

    def undo(self):
        self.model.textures.insert(self.index, self.texture)


class ExplorerWidget(QtWidgets.QWidget):

    currentMaterialChanged = QtCore.pyqtSignal(int)
    currentTextureChanged = QtCore.pyqtSignal(int)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.model = None
        self.adaptor = None
        self.undo_stack = None

        self.tree_view = QtWidgets.QTreeView()
        self.tree_view.setHeaderHidden(True)
        self.tree_view.setDragEnabled(True)
        self.tree_view.setDragDropMode(QtWidgets.QTreeView.InternalMove)

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

    def setModel(self, model):
        self.model = model
        self.adaptor = ModelAdaptor(model, self.undo_stack)
        self.tree_view.setModel(self.adaptor)
        self.adaptor.rowsInserted.connect(self.on_rowsInserted)
        self.adaptor.rowsRemoved.connect(self.on_rowsRemoved)
        self.adaptor.rowDropped.connect(self.on_rowDropped)
        self.tree_view.selectionModel().currentRowChanged.connect(self.on_currentRowChanged)

    def setCurrentTexture(self, texture_index):
        index = self.adaptor.get_texture_index(texture_index)
        self.tree_view.setCurrentIndex(index)

    def emit_current_changed(self):
        current = self.tree_view.currentIndex()
        path = current.data(PathRole)
        if path is None:
            return
        if path.match(+_p.materials[...]):
            index = path[-1].key
            self.currentMaterialChanged.emit(index)
        elif path.match(+_p.textures[...]):
            index = path[-1].key
            self.currentTextureChanged.emit(index)

    def import_texture(self):
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            caption='Import Texture',
            directory=os.path.dirname(self.model.file_path),
            filter='BTI texture (*.bti);;All files (*)'
        )
        if not file_path:
            return
        try:
            texture = views.texture.Texture.load(file_path)
        except (FileNotFoundError, IsADirectoryError, PermissionError) as error:
            message = QtWidgets.QMessageBox()
            message.setIcon(QtWidgets.QMessageBox.Warning)
            message.setText(f"Could not open file '{error.filename}'")
            message.setInformativeText(error.strerror)
            message.exec_()
            return
        # Insert the texture at the end of the texture list
        index = len(self.model.textures)
        command = InsertTextureCommand(self.model, index, texture)
        self.undo_stack.push(command)
        self.setCurrentTexture(index)

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
        command = RemoveTextureCommand(self.model, index)
        self.undo_stack.push(command)

    def contextMenuEvent(self, event):
        index = self.tree_view.indexAt(event.pos())
        path = index.data(PathRole)
        if path is None:
            return
        if path == +_p.textures:
            menu = QtWidgets.QMenu(self)
            menu.addAction(self.action_import)
            menu.exec_(self.mapToGlobal(event.pos()))
        elif path.match(+_p.textures[...]):
            menu = QtWidgets.QMenu(self)
            menu.addAction(self.action_import)
            menu.addAction(self.action_export)
            menu.addAction(self.action_remove)
            menu.exec_(self.mapToGlobal(event.pos()))
        super().contextMenuEvent(event)

    @QtCore.pyqtSlot(QtCore.QModelIndex, QtCore.QModelIndex)
    def on_currentRowChanged(self, current, previous):
        self.emit_current_changed()

    @QtCore.pyqtSlot(QtCore.QModelIndex, int, int)
    def on_rowsInserted(self, parent, first, last):
        current = self.tree_view.currentIndex()
        if current.parent() != parent:
            return
        if current.row() < first or current.row() > last:
            return
        self.emit_current_changed()

    @QtCore.pyqtSlot(QtCore.QModelIndex, int, int)
    def on_rowsRemoved(self, parent, first, last):
        current = self.tree_view.currentIndex()
        if current.parent() != parent:
            return
        if current.row() < first or current.row() > last:
            return
        self.emit_current_changed()

    @QtCore.pyqtSlot(QtCore.QModelIndex, int)
    def on_rowDropped(self, parent, row):
        index = self.adaptor.index(row, 0, parent)
        self.tree_view.setCurrentIndex(index)

    @QtCore.pyqtSlot()
    def on_action_import_triggered(self):
        index = self.tree_view.currentIndex()
        path = index.data(PathRole)
        if path is None:
            return
        if path == +_p.textures or path.match(+_p.textures[...]):
            self.import_texture()

    @QtCore.pyqtSlot()
    def on_action_export_triggered(self):
        index = self.tree_view.currentIndex()
        path = index.data(PathRole)
        if path is None:
            return
        if path.match(+_p.textures[...]):
            index = path[-1].key
            self.export_texture(index)

    @QtCore.pyqtSlot()
    def on_action_remove_triggered(self):
        index = self.tree_view.currentIndex()
        path = index.data(PathRole)
        if path is None:
            return
        if path.match(+_p.textures[...]):
            index = path[-1].key
            self.remove_texture(index)

