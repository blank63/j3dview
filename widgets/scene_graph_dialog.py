from PyQt5.QtCore import Qt
from PyQt5 import QtCore, QtWidgets
from modelview.path import PATH_BUILDER as _p
from models.model import NodeType
from widgets.modelview import ItemModelBox, TreeView, ItemDelegate
from widgets.item_model_adaptor import (
    Entry,
    Item,
    AbstractListItem,
    ItemModelAdaptor
)


NodeTypeRole = Qt.UserRole + 1


class NodeItem(AbstractListItem):

    def __init__(self, entries=tuple(), *, node_path, **kwargs):
        super().__init__(entries, **kwargs)
        self.node_path = node_path
        self.list_path = node_path + _p.children

    def create_joint_item(self, path, node):
        joint = self.model.get_object_data(+_p.joints[node.index])
        entry = Entry(
            data=joint.name,
            role_data={NodeTypeRole: NodeType.JOINT}
        )
        return NodeItem([entry], node_path=path)

    def create_material_item(self, path, node):
        entry = Entry(
            path=path + _p.material.name,
            role_paths={Qt.UserRole: path + _p.material},
            role_data={NodeTypeRole: NodeType.MATERIAL},
            label='material',
            editable=True
        )
        return NodeItem([entry], node_path=path)

    def create_shape_item(self, path, node):
        entry = Entry(
            data=node.index,
            role_data={NodeTypeRole: NodeType.SHAPE}
        )
        return NodeItem([entry], node_path=path)

    def create_child(self, index):
        child_path = self.node_path + _p.children[index]
        child_node = self.model.get_object_data(child_path)
        if child_node.node_type == NodeType.JOINT:
            return self.create_joint_item(child_path, child_node)
        if child_node.node_type == NodeType.MATERIAL:
            return self.create_material_item(child_path, child_node)
        if child_node.node_type == NodeType.SHAPE:
            return self.create_shape_item(child_path, child_node)
        assert False


class MaterialListItem(AbstractListItem):

    def __init__(self):
        super().__init__(column_count=1)
        self.list_path = +_p

    def create_child(self, index):
        return Item([Entry(
            path=+_p[index].name,
            role_paths={Qt.UserRole: +_p[index]}
        )])


class Delegate(ItemDelegate):

    def __init__(self):
        super().__init__()
        self.material_list_adaptor = ItemModelAdaptor(root_item=MaterialListItem())
        self.prefix_table = {
            NodeType.JOINT: 'Joint: ',
            NodeType.MATERIAL: 'Material: ',
            NodeType.SHAPE: 'Shape: '
        }

    def setMaterials(self, materials):
        self.material_list_adaptor.setObjectModel(materials)

    def clear(self):
        self.material_list_adaptor.setObjectModel(None)

    def sizeHint(self, option, index):
        option = QtWidgets.QStyleOptionViewItem(option)
        self.initStyleOption(option, index)
        node_type = index.data(NodeTypeRole)
        prefix = self.prefix_table[node_type]
        text = prefix + str(index.data())
        return option.fontMetrics.size(0, text)

    def paint(self, painter, option, index):
        option = QtWidgets.QStyleOptionViewItem(option)
        self.initStyleOption(option, index)
        node_type = index.data(NodeTypeRole)
        prefix = self.prefix_table[node_type]
        text = prefix + str(index.data())
        painter.drawText(option.rect, 0, text)

    def createEditor(self, parent, option, index):
        editor = ItemModelBox(parent)
        editor.setModel(self.material_list_adaptor)
        editor.activated.connect(self.on_editor_activated)
        return editor

    def updateEditorGeometry(self, editor, option, index):
        option = QtWidgets.QStyleOptionViewItem(option)
        self.initStyleOption(option, index)
        node_type = index.data(NodeTypeRole)
        prefix = self.prefix_table[node_type]
        prefix_size = option.fontMetrics.size(0, prefix)
        available_width = option.rect.width() - prefix_size.width()
        width = min(available_width, editor.sizeHint().width())
        editor.setGeometry(
            option.rect.x() + prefix_size.width(),
            option.rect.y(),
            width,
            option.rect.height()
        )

    def setEditorData(self, editor, index):
        editor.setCurrentData(index.data(Qt.UserRole))

    def setModelData(self, editor, model, index):
        model.setData(index, editor.currentData(), Qt.UserRole)

    @QtCore.pyqtSlot(int)
    def on_editor_activated(self, index):
        self.commitData.emit(self.sender())
        self.editingFinished.emit(self.sender())


class DeepTreeView(TreeView):

    def scrollTo(self, index, hint=TreeView.EnsureVisible):
        # The default implementation uses the horizontal header to find the
        # horizontal start of an item. This does not work very well when the
        # tree is very deep, and the item is indented several levels. This is an
        # issue in particular because scrollTo is called when editing of an item
        # starts. We override this behaviour, and simply keep the previous
        # horizontal scroll position.
        horizontal_scroll = self.horizontalScrollBar().value()
        super().scrollTo(index, hint)
        self.horizontalScrollBar().setValue(horizontal_scroll)


class SceneGraphDialog(QtWidgets.QDialog):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setWindowTitle('Scene Graph Dialog')

        root_item = NodeItem(column_count=1, node_path=+_p.scene_graph)
        self.model_adaptor = ItemModelAdaptor(root_item=root_item)
        self.tree_view = DeepTreeView()
        self.tree_view.setHeaderHidden(True)
        self.tree_view.header().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        self.tree_view.header().setStretchLastSection(False)
        self.tree_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.tree_view.setEditTriggers(
            QtWidgets.QTreeView.CurrentChanged |
            QtWidgets.QTreeView.SelectedClicked
        )
        self.tree_view.setModel(self.model_adaptor)
        self.delegate = Delegate()
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
        self.model_adaptor.setUndoStack(undo_stack)

    def setModel(self, model):
        self.model_adaptor.setObjectModel(model)
        self.delegate.setMaterials(model.materials)
        self.tree_view.expandAll()

    def clear(self):
        self.model_adaptor.setObjectModel(None)
        self.delegate.clear()

