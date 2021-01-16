import io
import pkgutil
from PyQt5 import QtCore, QtWidgets, uic
from modelview.path import PATH_BUILDER as _p
from modelview.object_model import ItemInsertEvent, ItemRemoveEvent
from models.model import NodeType
from widgets.view_form import Item, ItemModelAdaptor, ItemModelBox, CommitViewValueCommand


class NodeItem(Item):

    def __init__(self, path):
        super().__init__()
        self.path = path

    @property
    def node(self):
        return self.path.get_value(self.model.view)

    @property
    def column_count(self):
        return 1

    def get_flags(self, column):
        return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

    @staticmethod
    def create_node(node_type, path):
        if node_type == NodeType.JOINT:
            return JointItem(path)
        if node_type == NodeType.MATERIAL:
            return MaterialItem(path)
        if node_type == NodeType.SHAPE:
            return ShapeItem(path)
        assert False

    def initialize(self):
        for i, node in enumerate(self.node.children):
            item = self.create_node(node.node_type, self.path + _p.children[i])
            self.model.add_item(item, self)
            item.initialize()


class JointItem(NodeItem):

    @property
    def joint(self):
        return self.model.view.joints[self.node.index]

    def get_data(self, column, role):
        if role != QtCore.Qt.DisplayRole:
            return QtCore.QVariant()
        return f'Joint: {self.joint.name}'


class MaterialItem(NodeItem):

    def __init__(self, path):
        super().__init__(path)
        self.triggers = frozenset((path + _p.material, path + _p.material.name))

    @property
    def material(self):
        return self.node.material

    def get_flags(self, column):
        return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEditable

    def get_data(self, column, role):
        if role == QtCore.Qt.DisplayRole:
            return f'Material: {self.material.name}'
        if role == QtCore.Qt.EditRole:
            return self.material
        return QtCore.QVariant()

    def set_data(self, column, value, role):
        if role != QtCore.Qt.EditRole:
            return False
        self.model.commit_view_value('Material', self.path + _p.material, value)
        return True

    def handle_event(self, event, path):
        self.model.item_data_changed(self)


class ShapeItem(NodeItem):

    def get_data(self, column, role):
        if role != QtCore.Qt.DisplayRole:
            return QtCore.QVariant()
        return f'Shape {self.node.index}'


class SceneGraphAdaptor(ItemModelAdaptor):

    def __init__(self, model, undo_stack):
        super().__init__(model)
        self.undo_stack = undo_stack
        self.set_header_labels('Node')
        for i, node in enumerate(model.scene_graph.children):
            item = NodeItem.create_node(node.node_type, +_p.scene_graph.children[i])
            self.add_item(item)
            item.initialize()

    def commit_view_value(self, label, path, value):
        command = CommitViewValueCommand(f"Changed '{label}'", self.view, path, value)
        self.undo_stack.push(command)


class MaterialListItem(Item):

    def __init__(self, index):
        super().__init__()
        self.index = index
        self.triggers = frozenset((+_p[index].name,))

    @property
    def column_count(self):
        return 1

    def get_flags(self, column):
        return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

    def get_data(self, column, role):
        if role == QtCore.Qt.DisplayRole:
            return self.model.view[self.index].name
        if role == QtCore.Qt.UserRole:
            return self.model.view[self.index]
        return QtCore.QVariant()

    def handle_event(self, event, path):
        self.model.item_data_changed(self)


class MaterialListAdaptor(ItemModelAdaptor):

    def __init__(self, materials):
        super().__init__(materials)
        self.set_header_labels(['Value'])
        for i in range(len(materials)):
            self.add_item(MaterialListItem(i))

    def handle_event(self, event, path):
        if path.match(+_p):
            if isinstance(event, ItemInsertEvent):
                row = event.index
                material_index = len(self.view) - 1
                self.beginInsertRows(QtCore.QModelIndex(), row, row)
                self.add_item(MaterialListItem(material_index))
                self.endInsertRows()
            elif isinstance(event, ItemRemoveEvent):
                row = event.index
                self.beginRemoveRows(QtCore.QModelIndex(), row, row)
                self.take_item(self.rowCount() - 1)
                self.endRemoveRows()
        super().handle_event(event, path)


class MaterialListDelegate(QtWidgets.QStyledItemDelegate):

    def __init__(self):
        super().__init__()
        self.adaptor = None

    def setMaterials(self, materials):
        self.adaptor = MaterialListAdaptor(materials)

    def clear(self):
        self.adaptor = None

    def createEditor(self, parent, option, index):
        editor = ItemModelBox(parent)
        editor.setModel(self.adaptor)
        editor.activated.connect(self.on_editor_activated)
        return editor

    def updateEditorGeometry(self, editor, option, index):
        prefix_size = option.fontMetrics.size(0, 'Material: ')
        available_width = option.rect.width() - prefix_size.width()
        width = min(available_width, editor.sizeHint().width())
        editor.setGeometry(
            option.rect.x() + prefix_size.width(),
            option.rect.y(),
            width,
            option.rect.height()
        )

    def setEditorData(self, editor, index):
        editor.setCurrentData(index.data(QtCore.Qt.EditRole))

    def setModelData(self, editor, model, index):
        model.setData(index, editor.currentData(), QtCore.Qt.EditRole)

    @QtCore.pyqtSlot(int)
    def on_editor_activated(self, index):
        self.commitData.emit(self.sender())


class SceneGraphDialog(QtWidgets.QDialog):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setWindowTitle('Scene Graph Dialog')

        self.undo_stack = None

        self.tree_view = QtWidgets.QTreeView()
        self.tree_view.setHeaderHidden(True)
        self.tree_view.header().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        self.tree_view.setEditTriggers(
            QtWidgets.QTreeView.CurrentChanged |
            QtWidgets.QTreeView.SelectedClicked
        )
        self.delegate = MaterialListDelegate()
        self.tree_view.setItemDelegate(self.delegate)

        self.button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        self.layout = QtWidgets.QVBoxLayout()
        self.layout.setContentsMargins(4, 4, 4, 4)
        self.layout.addWidget(self.tree_view)
        self.layout.addWidget(self.button_box)
        self.setLayout(self.layout)

    def setUndoStack(self, undo_stack):
        self.undo_stack = undo_stack

    def setModel(self, model):
        adaptor = SceneGraphAdaptor(model, self.undo_stack)
        self.delegate.setMaterials(model.materials)
        self.tree_view.setModel(adaptor)
        self.tree_view.expandAll()

    def clear(self):
        self.tree_view.setModel(None)
        self.delegate.clear()


class ModelForm(QtWidgets.QWidget):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ui = uic.loadUi(io.BytesIO(pkgutil.get_data(__package__, 'ModelForm.ui')), self)
        self.model = None
        self.scene_graph_dialog = SceneGraphDialog()
        self.scene_graph_dialog.finished.connect(self.on_scene_graph_dialog_finished)
        self.setEnabled(False)

    def setUndoStack(self, undo_stack):
        self.scene_graph_dialog.setUndoStack(undo_stack)

    def setModel(self, model):
        self.model = model

        if model.subversion == b'\xFF\xFF\xFF\xFF':
            self.subversion.setText('0')
        elif model.subversion == b'SVR3':
            self.subversion.setText('3')
        else:
            self.subversion.setText('unknown')

        self.unknown0.setText(str(model.scene_graph.unknown0))

        self.add_vertex_array(model.position_array)
        self.add_vertex_array(model.normal_array)
        for array in model.color_arrays:
            self.add_vertex_array(array)
        for array in model.texcoord_arrays:
            self.add_vertex_array(array)

        if not self.scene_graph_dialog.isHidden():
            self.scene_graph_dialog.setModel(model)

        self.setEnabled(True)

    def add_vertex_array(self, array):
        if array is None:
            return
        info = ', '.join((
            array.attribute.name,
            array.component_type.name,
            array.component_count.name
        ))
        self.vertex_array_info.appendPlainText(info)

    def clear(self):
        self.model = None
        self.subversion.clear()
        self.unknown0.clear()
        self.vertex_array_info.clear()
        self.scene_graph_dialog.clear()
        self.setEnabled(False)

    @QtCore.pyqtSlot(bool)
    def on_scene_graph_button_clicked(self, checked):
        self.scene_graph_dialog.setModel(self.model)
        self.scene_graph_dialog.show()
        self.scene_graph_dialog.raise_()
        self.scene_graph_dialog.activateWindow()

    @QtCore.pyqtSlot(int)
    def on_scene_graph_dialog_finished(self, result):
        self.scene_graph_dialog.clear()

