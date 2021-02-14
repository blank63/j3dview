from PyQt5.QtCore import Qt
from PyQt5 import QtCore, QtGui, QtWidgets


class UndoCommand(QtWidgets.QUndoCommand):
    pass


class UndoStack(QtWidgets.QUndoStack):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.active_command = None
        self.indexChanged.connect(self.on_indexChanged)

    def push(self, command):
        if command.isObsolete():
            return
        if self.active_command is not None:
            assert self.active_command is self.command(self.index() - 1)
            if self.active_command.mergeWith(command):
                command.redo()
                if self.active_command.isObsolete():
                    self.undo()
                return
        super().push(command)
        if command is self.command(self.index() - 1):
            self.active_command = command

    def commitActiveCommand(self):
        self.active_command = None

    @QtCore.pyqtSlot(int)
    def on_indexChanged(self, index):
        self.commitActiveCommand()


class AbstractItemModel(QtCore.QAbstractItemModel):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.undo_stack = None

    def setUndoStack(self, undo_stack):
        self.undo_stack = undo_stack

    def submit(self):
        assert self.undo_stack is not None
        self.undo_stack.commitActiveCommand()
        return True


class ItemDelegate(QtWidgets.QStyledItemDelegate):

    editingFinished = QtCore.pyqtSignal(QtWidgets.QWidget)

    def initEditor(self, editor):
        pass


class ItemDelegateDelegate(ItemDelegate):
    """Delegate that delegates to other delegates."""

    def get_delegate(self, index):
        return super()

    def sizeHint(self, option, index):
        return self.get_delegate(index).sizeHint(option, index)

    def paint(self, painter, option, index):
        self.get_delegate(index).paint(painter, option, index)

    def editorEvent(self, event, model, option, index):
        return self.get_delegate(index).editorEvent(event, model, option, index)

    def helpEvent(self, event, view, option, index):
        return self.get_delegate(index).helpEvent(event, view, option, index)

    def createEditor(self, parent, option, index):
        return self.get_delegate(index).createEditor(parent, option, index)

    def destroyEditor(self, editor, index):
        self.get_delegate(index).destroyEditor(editor, index)

    def sizeHint(self, option, index):
        return self.get_delegate(index).sizeHint(option, index)

    def updateEditorGeometry(self, editor, option, index):
        self.get_delegate(index).updateEditorGeometry(editor, option, index)

    def setEditorData(self, editor, index):
        self.get_delegate(index).setEditorData(editor, index)

    def setModelData(self, editor, model, index):
        self.get_delegate(index).setModelData(editor, model, index)


class TreeView(QtWidgets.QTreeView):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        delegate = ItemDelegate()
        delegate.editingFinished.connect(self.on_delegate_editingFinished)
        super().setItemDelegate(delegate)

    def setItemDelegate(self, delegate):
        self.itemDelegate().editingFinished.disconnect(self.on_delegate_editingFinished)
        delegate.editingFinished.connect(self.on_delegate_editingFinished)
        super().setItemDelegate(delegate)

    @QtCore.pyqtSlot(QtWidgets.QWidget)
    def on_delegate_editingFinished(self, editor):
        self.model().submit()


class DataWidgetMapper(QtWidgets.QDataWidgetMapper):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        delegate = ItemDelegate()
        delegate.editingFinished.connect(self.on_delegate_editingFinished)
        super().setItemDelegate(delegate)

    def setModel(self, model):
        if self.model() is not None:
            self.model().modelReset.disconnect(self.on_model_modelReset)
        model.modelReset.connect(self.on_model_modelReset)
        super().setModel(model)

    def setItemDelegate(self, delegate):
        self.itemDelegate().editingFinished.disconnect(self.on_delegate_editingFinished)
        delegate.editingFinished.connect(self.on_delegate_editingFinished)
        super().setItemDelegate(delegate)

    @QtCore.pyqtSlot()
    def on_model_modelReset(self):
        self.toFirst()

    @QtCore.pyqtSlot(QtWidgets.QWidget)
    def on_delegate_editingFinished(self, editor):
        self.model().submit()


class DataDelegateMapper(ItemDelegateDelegate):

    def __init__(self):
        super().__init__()
        self.mapping_table = {}

    def addMapping(self, delegate, section):
        self.mapping_table[section] = delegate
        delegate.commitData.connect(self.commitData.emit)
        delegate.editingFinished.connect(self.editingFinished.emit)
        delegate.closeEditor.connect(self.closeEditor.emit)

    def get_delegate(self, index):
        return self.mapping_table[index.row()]


class ItemModelBox(QtWidgets.QComboBox):

    EMPTY_MODEL = QtGui.QStandardItemModel()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._current_data = None
        self.model().rowsInserted.connect(self.on_rowsInserted)

    def setCurrentData(self, data):
        index = self.findData(data)
        assert index != -1
        self.setCurrentIndex(index)
        self._current_data = data

    def setModel(self, model):
        self.model().rowsInserted.disconnect(self.on_rowsInserted)
        model.rowsInserted.connect(self.on_rowsInserted)
        super().setModel(model)

    def clear(self):
        self._current_data = None
        self.setModel(self.EMPTY_MODEL)

    @QtCore.pyqtSlot(QtCore.QModelIndex, int, int)
    def on_rowsInserted(self, parent, first, last):
        # When a row is moved in the model by removing and then inserting it, the
        # current index might need to be updated
        if self._current_data == self.currentData():
            return
        index = self.findData(self._current_data)
        assert index != -1
        self.setCurrentIndex(index)


class CheckBoxDelegate(ItemDelegate):

    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        option.features &= ~QtWidgets.QStyleOptionViewItem.HasDisplay
        option.text = None
        option.features |= QtWidgets.QStyleOptionViewItem.HasCheckIndicator
        if index.data(Qt.EditRole):
            option.checkState = Qt.Checked
        else:
            option.checkState = Qt.Unchecked

    def editorEvent(self, event, model, option, index):
        # Adapted from QStyledItemDelegate.editorEvent(). The model data is
        # changed when clicking the left mouse button inside the checkbox, or
        # when the space key or the select key is pressed while the item is
        # selected.
        #TODO Clicking anywhere, and then dragging the cursor inside the checkbox
        # and releasing also counts as a click.
        if not option.state & QtWidgets.QStyle.State_Enabled:
            return False
        if not index.flags() & Qt.ItemIsEnabled:
            return False

        if option.widget is not None:
            style = option.widget.style()
        else:
            style = QtCore.QApplication.style()

        if event.type() == QtCore.QEvent.MouseButtonRelease:
            if event.button() != Qt.LeftButton:
                return False
            option = QtWidgets.QStyleOptionViewItem(option)
            self.initStyleOption(option, index)
            check_rect = style.subElementRect(QtWidgets.QStyle.SE_ItemViewItemCheckIndicator, option, option.widget)
            if not check_rect.contains(event.pos()):
                return False
        elif event.type() == QtCore.QEvent.KeyPress:
            if event.key() not in {Qt.Key_Space, Qt.Key_Select}:
                return False
        else:
            return False

        value = index.data(Qt.EditRole)
        model.setData(index, not value)
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
        self.editingFinished.emit(self.sender())


class ComboBoxDelegate(ItemDelegate):

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

    def setEditorData(self, editor, index):
        data = index.data(Qt.EditRole)
        if data is None:
            # No data, set editor to default position
            editor.setCurrentIndex(0)
            return
        i = editor.findData(data)
        assert i != -1
        editor.setCurrentIndex(i)

    def setModelData(self, editor, model, index):
        model.setData(index, editor.currentData())

    @QtCore.pyqtSlot(int)
    def on_editor_activated(self, index):
        self.commitData.emit(self.sender())
        self.editingFinished.emit(self.sender())


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


class ItemModelBoxDelegate(ItemDelegate):

    def initEditor(self, editor):
        editor.activated.connect(self.on_editor_activated)

    def createEditor(self, parent, option, index):
        editor = ItemModelBox(parent)
        self.initEditor(editor)
        return editor

    def clearEditor(self, editor):
        editor.clear()

    def setEditorData(self, editor, index):
        editor.setCurrentData(index.data(Qt.EditRole))

    def setModelData(self, editor, model, index):
        model.setData(index, editor.currentData())

    @QtCore.pyqtSlot(int)
    def on_editor_activated(self, index):
        self.commitData.emit(self.sender())
        self.editingFinished.emit(self.sender())


class LineEditDelegate(ItemDelegate):

    def initEditor(self, editor):
        editor.textEdited.connect(self.on_editor_textEdited)
        editor.editingFinished.connect(self.on_editor_editingFinished)

    def setEditorData(self, editor, index):
        if editor.hasFocus():
            # Setting the text of a QLineEdit clears the widgets undo history.
            # We do not want that to happen when the user is editing.
            return
        super().setEditorData(editor, index)

    @QtCore.pyqtSlot(str)
    def on_editor_textEdited(self, value):
        self.commitData.emit(self.sender())

    @QtCore.pyqtSlot()
    def on_editor_editingFinished(self):
        self.editingFinished.emit(self.sender())


class SpinBoxDelegate(ItemDelegate):

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
        editor.editingFinished.connect(self.on_editor_editingFinished)

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
            # programmatically. Assume that the user made the change if the
            # editor has focus.
            self.commitData.emit(editor)

    @QtCore.pyqtSlot()
    def on_editor_editingFinished(self):
        self.editingFinished.emit(self.sender())


class DoubleSpinBoxDelegate(ItemDelegate):

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
        editor.editingFinished.connect(self.on_editor_editingFinished)

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
            # programmatically. Assume that the user made the change if the
            # editor has focus.
            self.commitData.emit(editor)

    @QtCore.pyqtSlot()
    def on_editor_editingFinished(self):
        self.editingFinished.emit(self.sender())


class MatrixDelegate(ItemDelegate):

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


class ColorButtonDelegate(ItemDelegate):

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
        color = index.data(Qt.EditRole)
        if color is None:
            color = Color()
        self.color =color 
        self.pixmap.fill(QtGui.QColor(color.r, color.g, color.b))
        self.editor.setIcon(QtGui.QIcon(self.pixmap))

    def setModelData(self, editor, model, index):
        model.setData(index, self.color)

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
        elif action == QtWidgets.QDialog.Accepted:
            self.color = self._from_qcolor(dialog.selectedColor())
        else:
            assert False
        self.commitData.emit(self.editor)
        self.editingFinished.emit(self.editor)

    @QtCore.pyqtSlot(QtGui.QColor)
    def on_dialog_currentColorChanged(self, color):
        self.color = self._from_qcolor(color)
        self.commitData.emit(self.editor)

