from enum import Enum
from PyQt5 import QtCore, QtWidgets
import views
from views import path_builder as _p
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
        return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

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

    def __init__(self, model):
        super().__init__(model)
        self.set_header_labels(['Value'])
        self.material_list = ListItem('Materials', +_p.materials)
        self.add_item(self.material_list)
        self.material_list.initialize()
        self.texture_list = ListItem('Textures', +_p.textures)
        self.add_item(self.texture_list)
        self.texture_list.initialize()

    def handle_event(self, event, path):
        if path.match(+_p.textures[...]):
            self.texture_list.handle_event(event, path)
        super().handle_event(event, path)


class RemoveTextureCommand(QtWidgets.QUndoCommand):
    #TODO: Should something be done about textures that are no longer being
    # used, but are still in the undo stack?

    def __init__(self, model, texture_index):
        super().__init__()
        self.model = model
        self.texture_index = texture_index
        self.texture = model.textures[texture_index]
        self.setText(f'Remove texture {self.texture.name}')

    def redo(self):
        self.model.remove_texture(self.texture_index)

    def undo(self):
        self.model.insert_texture(self.texture_index, self.texture)


class ExplorerWidget(QtWidgets.QWidget):

    currentMaterialChanged = QtCore.pyqtSignal(int)
    currentTextureChanged = QtCore.pyqtSignal(int)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.model = None
        self.undo_stack = None

        self.tree_view = QtWidgets.QTreeView()
        self.tree_view.setHeaderHidden(True)

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.tree_view)
        self.setLayout(layout)

        self.action_remove = QtWidgets.QAction('Remove')
        self.action_remove.triggered.connect(self.on_action_remove_triggered)
        self.addAction(self.action_remove)

    def setUndoStack(self, undo_stack):
        self.undo_stack = undo_stack

    def setModel(self, model):
        self.model = model
        adaptor = ModelAdaptor(model)
        self.tree_view.setModel(adaptor)
        adaptor.rowsInserted.connect(self.on_rowsInserted)
        adaptor.rowsRemoved.connect(self.on_rowsRemoved)
        self.tree_view.selectionModel().currentRowChanged.connect(self.on_currentRowChanged)

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
        if path.match(+_p.textures[...]):
            menu = QtWidgets.QMenu(self)
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

    @QtCore.pyqtSlot()
    def on_action_remove_triggered(self):
        index = self.tree_view.currentIndex()
        path = index.data(PathRole)
        if path is None:
            return
        if path.match(+_p.textures[...]):
            index = path[-1].key
            self.remove_texture(index)


