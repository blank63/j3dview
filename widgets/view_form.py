from PyQt5 import QtCore, QtGui, QtWidgets
import views


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


class WidgetHandler(QtCore.QObject):

    updateValue = QtCore.pyqtSignal(object)
    commitValue = QtCore.pyqtSignal(object, object)

    def __init__(self):
        super().__init__()
        self.current_value = None
        self.transaction_started = False

    def update_widget(self, value):
        pass

    def setValue(self, value):
        if self.transaction_started:
            # Ignore attempts to set the value programmatically when the user is
            # editing the value
            return
        self.current_value = value
        self.update_widget(value)

    def clear_widget(self):
        pass

    def clear(self):
        self.current_value = None
        self.transaction_started = False
        self.clear_widget()

    def begin_transaction(self):
        self.transaction_started = True

    def commit(self, value):
        if value != self.current_value:
            self.commitValue.emit(self.current_value, value)
        self.current_value = value
        self.transaction_started = False

    def rollback(self):
        self.updateValue.emit(self.current_value)
        self.transaction_started = False


class LineEditHandler(WidgetHandler):

    def __init__(self, widget):
        super().__init__()
        self.widget = widget
        widget.textEdited.connect(self.on_textEdited)
        widget.editingFinished.connect(self.on_editingFinished)

    def update_widget(self, value):
        self.widget.setText(value)

    def clear_widget(self):
        self.widget.clear()

    @QtCore.pyqtSlot(str)
    def on_textEdited(self, value):
        self.begin_transaction()
        self.updateValue.emit(value)

    @QtCore.pyqtSlot()
    def on_editingFinished(self):
        self.commit(self.widget.text())


class ComboBoxHandler(WidgetHandler):

    def __init__(self, widget):
        super().__init__()
        self.widget = widget
        widget.activated.connect(self.on_activated)

    def update_widget(self, value):
        index = self.widget.findData(value)
        assert index != -1
        self.widget.setCurrentIndex(index)

    def clear_widget(self):
        self.widget.setCurrentIndex(0)

    @QtCore.pyqtSlot(int)
    def on_activated(self, index):
        self.commit(self.widget.itemData(index))


class SpinBoxHandler(WidgetHandler):

    def __init__(self, widget):
        super().__init__()
        self.widget = widget
        widget.valueChanged.connect(self.on_valueChanged)
        widget.editingFinished.connect(self.on_editingFinished)

    def update_widget(self, value):
        self.widget.setValue(value)

    def clear_widget(self):
        self.widget.clear()

    def on_valueChanged(self, value):
        if self.widget.hasFocus():
            # A transaction should only be started if it is the user who changes
            # the value, but valueChanged is also emitted when the value is
            # changed programmatically. Assume that the user made the change if
            # the widget has focus.
            self.begin_transaction()
        self.updateValue.emit(value)

    @QtCore.pyqtSlot()
    def on_editingFinished(self):
        self.commit(self.widget.value())


class CheckBoxHandler(WidgetHandler):

    def __init__(self, widget):
        super().__init__()
        self.widget = widget
        widget.clicked.connect(self.on_clicked)

    def update_widget(self, value):
        self.widget.setChecked(value)

    def clear_widget(self):
        self.widget.setChecked(False)

    @QtCore.pyqtSlot(bool)
    def on_clicked(self, value):
        self.commit(value)


class ColorButtonHandler(WidgetHandler):

    def __init__(self, widget):
        super().__init__()
        self.widget = widget
        self.pixmap = QtGui.QPixmap(widget.iconSize())
        self.clear_widget()
        widget.clicked.connect(self.on_clicked)

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

    def update_widget(self, value):
        self.pixmap.fill(QtGui.QColor(value.r, value.g, value.b))
        self.widget.setIcon(QtGui.QIcon(self.pixmap))

    def clear_widget(self):
        self.update_widget(Color())

    @QtCore.pyqtSlot(bool)
    def on_clicked(self, clicked):
        self.begin_transaction()
        dialog = QtWidgets.QColorDialog()
        dialog.setOptions(
            QtWidgets.QColorDialog.ShowAlphaChannel |
            QtWidgets.QColorDialog.DontUseNativeDialog
        )
        dialog.setCurrentColor(self._to_qcolor(self.current_value))
        dialog.currentColorChanged.connect(self.on_currentColorChanged)
        action = dialog.exec_()
        if action == QtWidgets.QDialog.Rejected:
            self.rollback()
        elif action == QtWidgets.QDialog.Accepted:
            color = self._from_qcolor(dialog.selectedColor())
            self.update_widget(color)
            self.commit(self._from_qcolor(dialog.selectedColor()))
        else:
            assert False

    @QtCore.pyqtSlot(QtGui.QColor)
    def on_currentColorChanged(self, color):
        self.updateValue.emit(self._from_qcolor(color))


class ViewForm(QtWidgets.QWidget):

    commitViewValue = QtCore.pyqtSignal(views.Path, object, object, str)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.handler_table = {}
        self.view = None
        self.setEnabled(False)

    def add_handler(self, path, handler, label):
        def update_callback(value):
            path.set_value(self.view, value)
        def commit_callback(old_value, new_value):
            self.commitViewValue.emit(path, old_value, new_value, label)
        handler.updateValue.connect(update_callback)
        handler.commitValue.connect(commit_callback)
        self.handler_table[path] = handler

    def setView(self, view):
        if self.view is not None:
            self.view.unregister_listener(self)
        self.view = view
        self.reload()
        self.view.register_listener(self)
        self.setEnabled(True)

    def reload(self):
        for path, handler in self.handler_table.items():
            handler.setValue(path.get_value(self.view))

    def clear(self):
        if self.view is not None:
            self.view.unregister_listener(self)
        self.view = None
        for handler in self.handler_table.values():
            handler.clear()
        self.setEnabled(False)

    def handle_event(self, event, path):
        if isinstance(event, views.ValueChangedEvent):
            handler = self.handler_table.get(path)
            if handler is not None:
                handler.setValue(path.get_value(self.view))

