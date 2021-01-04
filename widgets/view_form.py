import weakref
from PyQt5 import QtCore, QtGui, QtWidgets
import views


class Item:

    def __init__(self):
        self.model_reference = None
        self.parent_reference = None
        self.children = []
        self.enabled = True
        self.triggers = frozenset()

    @property
    def parent(self):
        return self.parent_reference()

    @property
    def model(self):
        return self.model_reference()

    def set_parent(self, parent):
        self.parent_reference = weakref.ref(parent)

    def attach_model(self, model):
        self.model_reference = weakref.ref(model)
        for child in self.children:
            child.attach_model(model)
        for trigger in self.triggers:
            self.model.register_trigger(self, trigger)

    def detach_model(self):
        for trigger in self.triggers:
            self.model.unregister_trigger(self, trigger)
        for child in self.children:
            child.detach_model()
        self.model_reference = None

    def set_enabled(self, value):
        self.enabled = value
        for child in self.children:
            child.set_enabled(value)

    def add_child(self, child):
        child.set_parent(self)
        self.children.append(child)

    def take_child(self, row):
        child = self.children[row]
        del self.children[row]
        return child

    def get_child(self, row):
        return self.children[row]

    @property
    def child_count(self):
        return len(self.children)

    def get_child_index(self, child):
        return self.children.index(child)

    @property
    def column_count(self):
        return 0

    def get_flags(self, column):
        return QtCore.Qt.NoItemFlags

    def get_data(self, column, role):
        return QtCore.QVariant()

    def set_data(self, column, value, role):
        return False

    def handle_event(self, event, path):
        pass


class GroupItem(Item):

    def __init__(self, labels=[]):
        super().__init__()
        self.labels = labels

    def set_labels(self, labels):
        self.labels = labels

    @property
    def column_count(self):
        return len(self.labels)

    def get_flags(self, column):
        if not self.enabled:
            return QtCore.Qt.NoItemFlags
        return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

    def get_data(self, column, role):
        if role != QtCore.Qt.DisplayRole:
            return QtCore.QVariant()
        return self.labels[column]


class PropertyItem(Item):

    def __init__(self, label, path):
        super().__init__()
        self.label = label
        self.path = path
        self.triggers = frozenset((path,))

    @property
    def column_count(self):
        return 1

    def get_flags(self, column):
        if not self.enabled:
            return QtCore.Qt.NoItemFlags
        if column == 0:
            return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEditable
        assert False

    def get_data(self, column, role):
        if column != 0:
            return QtCore.QVariant()
        if role not in {QtCore.Qt.DisplayRole, QtCore.Qt.EditRole}:
            return QtCore.QVariant()
        return self.path.get_value(self.model.view)

    def set_data(self, column, value, role):
        if column != 0:
            return False
        if role != QtCore.Qt.EditRole:
            return False
        self.model.commitViewValue.emit(self.label, self.path, value)
        return True

    def handle_event(self, event, path):
        self.model.item_data_changed(self)


class ItemModelAdaptor(QtCore.QAbstractItemModel):

    commitViewValue = QtCore.pyqtSignal(str, views.Path, object)

    def __init__(self, view):
        super().__init__()
        self.root_item = GroupItem()
        self.view = view
        self.view.register_listener(self)
        self.trigger_table = {}

    def set_header_labels(self, labels):
        self.root_item.set_labels(labels)

    def register_trigger(self, item, path):
        self.trigger_table.setdefault(path, []).append(item)

    def unregister_trigger(self, item, path):
        self.trigger_table[path].remove(item)

    def add_item(self, item, parent_item=None):
        if parent_item is None:
            parent_item = self.root_item
        parent_item.add_child(item)
        item.attach_model(self)

    def take_item(self, row, parent_item=None):
        if parent_item is None:
            parent_item = self.root_item
        item = parent_item.take_child(row)
        item.detach_model()
        return item

    def get_item_index(self, item):
        if item is self.root_item:
            return QtCore.QModelIndex()
        row = item.parent.get_child_index(item)
        return self.createIndex(row, 0, item)

    def item_data_changed(self, item):
        left = self.get_item_index(item)
        right = self.sibling(left.row(), self.columnCount(left) - 1, left)
        self.dataChanged.emit(left, right)

    def index(self, row, column, parent=QtCore.QModelIndex()):
        if row < 0 or column < 0:
            return QtCore.QModelIndex()
        if parent.isValid():
            parent_item = parent.internalPointer()
        else:
            parent_item = self.root_item
        if row >= parent_item.child_count:
            return QtCore.QModelIndex()
        item = parent_item.get_child(row)
        if column >= item.column_count:
            return QtCore.QModelIndex()
        return self.createIndex(row, column, item)

    def parent(self, index):
        if not index.isValid():
            return QtCore.QModelIndex()
        item = index.internalPointer()
        parent_item = item.parent
        if parent_item is self.root_item:
            return QtCore.QModelIndex()
        row = parent_item.parent.get_child_index(parent_item)
        return self.createIndex(row, 0, parent_item)

    def rowCount(self, parent=QtCore.QModelIndex()):
        if parent.isValid():
            parent_item = parent.internalPointer()
        else:
            parent_item = self.root_item
        return parent_item.child_count

    def columnCount(self, parent=QtCore.QModelIndex()):
        if parent.isValid():
            parent_item = parent.internalPointer()
        else:
            parent_item = self.root_item
        return parent_item.column_count

    def flags(self, index):
        if not index.isValid():
            return QtCore.Qt.NoItemFlags
        item = index.internalPointer()
        return item.get_flags(index.column())

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid():
            return QtCore.QVariant()
        item = index.internalPointer()
        return item.get_data(index.column(), role)

    def setData(self, index, value, role=QtCore.Qt.EditRole):
        if not index.isValid():
            return False
        item = index.internalPointer()
        return item.set_data(index.column(), value, role)

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if orientation != QtCore.Qt.Horizontal:
            return QtCore.QVariant()
        if section < 0 or section >= self.root_item.column_count:
            return QtCore.QVariant()
        return self.root_item.get_data(section, role)

    def handle_event(self, event, path):
        for item in self.trigger_table.get(path, []):
            item.handle_event(event, path)


class CheckBoxDelegate(QtWidgets.QStyledItemDelegate):

    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        option.features &= ~QtWidgets.QStyleOptionViewItem.HasDisplay
        option.text = None
        option.features |= QtWidgets.QStyleOptionViewItem.HasCheckIndicator
        if index.data(QtCore.Qt.EditRole):
            option.checkState = QtCore.Qt.Checked
        else:
            option.checkState = QtCore.Qt.Unchecked

    def editorEvent(self, event, model, option, index):
        # Adapted from QStyledItemDelegate.editorEvent(). The model data is
        # changed when clicking the left mouse button inside the checkbox, or
        # when the space key or the select key is pressed while the item is
        # selected.
        #TODO Clicking anywhere, and then dragging the cursor inside the checkbox
        # and releasing also counts as a click.
        if not option.state & QtWidgets.QStyle.State_Enabled:
            return False
        if not index.flags() & QtCore.Qt.ItemIsEnabled:
            return False

        if option.widget is not None:
            style = option.widget.style()
        else:
            style = QtCore.QApplication.style()

        if event.type() == QtCore.QEvent.MouseButtonRelease:
            if event.button() != QtCore.Qt.LeftButton:
                return False
            option = QtWidgets.QStyleOptionViewItem(option)
            self.initStyleOption(option, index)
            check_rect = style.subElementRect(QtWidgets.QStyle.SE_ItemViewItemCheckIndicator, option, option.widget)
            if not check_rect.contains(event.pos()):
                return False
        elif event.type() == QtCore.QEvent.KeyPress:
            if event.key() not in {QtCore.Qt.Key_Space, QtCore.Qt.Key_Select}:
                return False
        else:
            return False

        value = index.data(QtCore.Qt.EditRole)
        model.setData(index, not value, QtCore.Qt.EditRole)
        return True

    def initEditor(self, editor):
        editor.clicked.connect(self.on_editor_clicked)

    def createEditor(self, parent, option, index):
        return None

    def clearEditor(self, editor):
        editor.setChecked(False)

    @QtCore.pyqtSlot(bool)
    def on_editor_clicked(self, checked):
        self.commitData.emit(self.sender())


class ComboBoxDelegate(QtWidgets.QStyledItemDelegate):

    def get_item_data(self):
        return []

    def initEditor(self, editor):
        for user_data in self.get_item_data():
            editor.addItem(self.displayText(user_data, editor.locale()), user_data)
        editor.activated.connect(self.on_editor_activated)

    def createEditor(self, parent, option, index):
        editor = QtWidgets.QComboBox(parent)
        self.initEditor(editor)
        return editor

    def clearEditor(self, editor):
        editor.setCurrentIndex(0)

    def setEditorData(self, editor, index):
        i = editor.findData(index.data(QtCore.Qt.EditRole))
        assert i != -1
        editor.setCurrentIndex(i)

    def setModelData(self, editor, model, index):
        model.setData(index, editor.currentData(), QtCore.Qt.EditRole)

    @QtCore.pyqtSlot(int)
    def on_editor_activated(self, index):
        self.commitData.emit(self.sender())


class CountDelegate(ComboBoxDelegate):

    def __init__(self, max_count):
        super().__init__()
        self.max_count = max_count

    def get_item_data(self):
        return range(self.max_count + 1)


class EnumDelegate(ComboBoxDelegate):

    def __init__(self, enum_type):
        super().__init__()
        self.enum_type = enum_type

    def get_item_data(self):
        return self.enum_type

    def displayText(self, value, locale):
        return super().displayText(value.name, locale)


class LineEditDelegate(QtWidgets.QStyledItemDelegate):

    def initEditor(self, editor):
        editor.textEdited.connect(self.on_editor_textEdited)

    def clearEditor(self, editor):
        editor.clear()

    @QtCore.pyqtSlot(str)
    def on_editor_textEdited(self, value):
        self.commitData.emit(self.sender())


class SpinBoxDelegate(QtWidgets.QStyledItemDelegate):

    def __init__(self, min, max, step=1):
        super().__init__()
        self.minimum = min
        self.maximum = max
        self.step = step

    def initEditor(self, editor):
        editor.setMinimum(self.minimum)
        editor.setMaximum(self.maximum)
        editor.setSingleStep(self.step)
        editor.valueChanged.connect(self.on_editor_valueChanged)

    def createEditor(self, parent, option, index):
        editor = QtWidgets.QSpinBox(parent)
        self.initEditor(editor)
        return editor

    def clearEditor(self, editor):
        editor.clear()

    @QtCore.pyqtSlot(int)
    def on_editor_valueChanged(self, value):
        editor = self.sender()
        if editor.hasFocus():
            # We should only commit the data when the user changes the value,
            # but valueChanged is also emitted when the value is changed
            # programmatically. Assume that the user made the change is the
            # editor has focus.
            self.commitData.emit(editor)


class DoubleSpinBoxDelegate(QtWidgets.QStyledItemDelegate):

    def __init__(self, min, max, step=1, decimals=2):
        super().__init__()
        self.minimum = min
        self.maximum = max
        self.step = step
        self.decimals = decimals

    def displayText(self, value, locale):
        return super().displayText(f'{value:.{self.decimals}f}', locale)

    def initEditor(self, editor):
        editor.setMinimum(self.minimum)
        editor.setMaximum(self.maximum)
        editor.setSingleStep(self.step)
        editor.setDecimals(self.decimals)
        editor.valueChanged.connect(self.on_editor_valueChanged)

    def createEditor(self, parent, option, index):
        editor = QtWidgets.QDoubleSpinBox(parent)
        self.initEditor(editor)
        return editor

    def clearEditor(self, editor):
        editor.clear()

    @QtCore.pyqtSlot(float)
    def on_editor_valueChanged(self, value):
        editor = self.sender()
        if editor.hasFocus():
            # We should only commit the data when the user changes the value,
            # but valueChanged is also emitted when the value is changed
            # programmatically. Assume that the user made the change is the
            # editor has focus.
            self.commitData.emit(editor)


class MatrixDelegate(QtWidgets.QStyledItemDelegate):

    def displayText(self, value, locale):
        text = '\n'.join(
            ', '.join(str(v) for v in c)
            for c in value
        )
        return super().displayText(text, locale)

    def sizeHint(self, option, index):
        option = QtWidgets.QStyleOptionViewItem(option)
        self.initStyleOption(option, index)
        return option.fontMetrics.size(0, option.text)

    def paint(self, painter, option, index):
        option = QtWidgets.QStyleOptionViewItem(option)
        self.initStyleOption(option, index)
        painter.drawText(option.rect, 0, option.text)

    def createEditor(self, parent, option, index):
        #TODO implement editing
        return None


class Color:

    def __init__(self, r=0, g=0, b=0, a=255):
        self.r = r
        self.g = g
        self.b = b
        self.a = a

    def __eq__(self, other):
        return (
            self.r == other.r and
            self.g == other.g and
            self.b == other.b and
            self.a == other.a
        )


class ColorButtonDelegate(QtWidgets.QStyledItemDelegate):

    def __init__(self):
        super().__init__()
        self.color = Color()
        self.pixmap = None
        #XXX This delegate holds a reference to a specific editor, and can
        # therefore not be shared in the same way other delegates can.
        self.editor = None

    @staticmethod
    def _to_qcolor(color):
        return QtGui.QColor(color.r, color.g, color.b, color.a)

    @staticmethod
    def _from_qcolor(color):
        return Color(
            color.red(),
            color.green(),
            color.blue(),
            color.alpha()
        )

    def initEditor(self, editor):
        self.pixmap = QtGui.QPixmap(editor.iconSize())
        self.editor = editor
        self.editor.clicked.connect(self.on_button_clicked)

    def clearEditor(self, editor):
        self.color = Color()
        self.pixmap.fill(QtGui.QColor(self.color.r, self.color.g, self.color.b))
        self.editor.setIcon(QtGui.QIcon(self.pixmap))

    def setEditorData(self, editor, index):
        self.color = index.data(QtCore.Qt.EditRole)
        self.pixmap.fill(QtGui.QColor(self.color.r, self.color.g, self.color.b))
        self.editor.setIcon(QtGui.QIcon(self.pixmap))

    def setModelData(self, editor, model, index):
        model.setData(index, self.color, QtCore.Qt.EditRole)

    @QtCore.pyqtSlot(bool)
    def on_button_clicked(self, checked):
        start_color = self.color
        dialog = QtWidgets.QColorDialog()
        dialog.setOptions(
            QtWidgets.QColorDialog.ShowAlphaChannel |
            QtWidgets.QColorDialog.DontUseNativeDialog
        )
        dialog.setCurrentColor(self._to_qcolor(self.color))
        dialog.currentColorChanged.connect(self.on_dialog_currentColorChanged)
        action = dialog.exec_()
        if action == QtWidgets.QDialog.Rejected:
            self.color = start_color
            self.commitData.emit(self.editor)
        elif action == QtWidgets.QDialog.Accepted:
            self.color = self._from_qcolor(dialog.selectedColor())
            self.commitData.emit(self.editor)
        else:
            assert False

    @QtCore.pyqtSlot(QtGui.QColor)
    def on_dialog_currentColorChanged(self, color):
        self.color = self._from_qcolor(color)
        self.commitData.emit(self.editor)


class DelegateDelegate(QtWidgets.QStyledItemDelegate):
    """Delegate that delegates to other delegates."""

    def get_delegate(self, item):
        return super()

    def sizeHint(self, option, index):
        return self.get_delegate(index).sizeHint(option, index)

    def paint(self, painter, option, index):
        self.get_delegate(index).paint(painter, option, index)

    def editorEvent(self, event, model, option, index):
        return self.get_delegate(index).editorEvent(event, model, option, index)

    def createEditor(self, parent, option, index):
        return self.get_delegate(index).createEditor(parent, option, index)

    def setEditorData(self, editor, index):
        self.get_delegate(index).setEditorData(editor, index)

    def setModelData(self, editor, model, index):
        self.get_delegate(index).setModelData(editor, model, index)


class ViewForm(QtWidgets.QWidget):

    commitViewValue = QtCore.pyqtSignal(str, views.Path, object)

    class Mapping:

        def __init__(self, label, path, widget, delegate):
            self.label = label
            self.path = path
            self.widget = widget
            self.delegate = delegate

    class Delegate(DelegateDelegate):

        def __init__(self):
            super().__init__()
            self.delegates = []

        def add_delegate(self, delegate):
            self.delegates.append(delegate)
            delegate.commitData.connect(self.commitData.emit)
            delegate.closeEditor.connect(self.closeEditor.emit)

        def get_delegate(self, index):
            return self.delegates[index.row()]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.view = None
        self.mappings = []
        self.mapper = None
        self.delegate = self.Delegate()
        self.setEnabled(False)

    def add_mapping(self, label, path, widget, delegate):
        self.mappings.append(self.Mapping(label, path, widget, delegate))
        delegate.initEditor(widget)
        self.delegate.add_delegate(delegate)

    def setView(self, view):
        self.view = view
        adaptor = ItemModelAdaptor(view)
        adaptor.set_header_labels(['Value'])
        for mapping in self.mappings:
            adaptor.add_item(PropertyItem(mapping.label, mapping.path))
        adaptor.commitViewValue.connect(self.commitViewValue.emit)
        self.mapper = QtWidgets.QDataWidgetMapper()
        self.mapper.setOrientation(QtCore.Qt.Vertical)
        self.mapper.setItemDelegate(self.delegate)
        self.mapper.setModel(adaptor)
        for i, mapping in enumerate(self.mappings):
            self.mapper.addMapping(mapping.widget, i)
        self.mapper.toFirst()
        self.setEnabled(True)

    def clear(self):
        self.view = None
        if self.mapper is not None:
            self.mapper.clearMapping()
        self.mapper = None
        for mapping in self.mappings:
            mapping.delegate.clearEditor(mapping.widget)
        self.setEnabled(False)

