import io
import pkgutil
from PyQt5 import QtCore, QtWidgets, uic
from views import path_builder as _p
from views.model import NodeType
from widgets.view_form import Item, ItemModelAdaptor


class NodeItem(Item):

    def __init__(self, path):
        super().__init__()
        self.path = path

    @property
    def column_count(self):
        return 1

    def get_flags(self, column):
        return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

    def get_data(self, column, role):
        if role != QtCore.Qt.DisplayRole:
            return QtCore.QVariant()
        node = self.path.get_value(self.model.view)
        if node.node_type == NodeType.JOINT:
            joint = self.model.view.joints[node.index]
            return f'Joint: {joint.name}'
        if node.node_type == NodeType.MATERIAL:
            material = self.model.view.materials[node.index]
            return f'Material: {material.name}'
        if node.node_type == NodeType.SHAPE:
            return f'Shape {node.index}'
        assert False

    def initialize(self):
        node = self.path.get_value(self.model.view)
        for i in range(len(node.children)):
            item = NodeItem(self.path + _p.children[i])
            self.model.add_item(item, self)
            item.initialize()


class SceneGraphDialog(QtWidgets.QDialog):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setWindowTitle('Scene Graph Dialog')

        self.tree_view = QtWidgets.QTreeView()
        self.tree_view.setHeaderHidden(True)
        self.tree_view.header().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)

        self.button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        self.layout = QtWidgets.QVBoxLayout()
        self.layout.setContentsMargins(4, 4, 4, 4)
        self.layout.addWidget(self.tree_view)
        self.layout.addWidget(self.button_box)
        self.setLayout(self.layout)

    def setModel(self, model):
        adaptor = ItemModelAdaptor(model)
        adaptor.set_header_labels('Node')
        for i in range(len(model.scene_graph.children)):
            item = NodeItem(+_p.scene_graph.children[i])
            adaptor.add_item(item)
            item.initialize()
        self.tree_view.setModel(adaptor)
        self.tree_view.expandAll()

    def clear(self):
        self.tree_view.setModel(None)


class ModelForm(QtWidgets.QWidget):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ui = uic.loadUi(io.BytesIO(pkgutil.get_data(__package__, 'ModelForm.ui')), self)
        self.model = None
        self.scene_graph_dialog = SceneGraphDialog()
        self.scene_graph_dialog.finished.connect(self.on_scene_graph_dialog_finished)
        self.setEnabled(False)

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

