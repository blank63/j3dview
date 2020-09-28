from PyQt5 import QtCore, QtGui, QtWidgets


class ComboBox(QtWidgets.QComboBox):

    def setCurrentData(self, value):
        index = self.findData(value)
        assert index != -1
        self.setCurrentIndex(index)

    def addEnumItems(self, enum_type):
        for value in enum_type:
            self.addItem(value.name, value)


class Color:

    def __init__(self, r=0, g=0, b=0, a=255):
        self.r = r
        self.g = g
        self.b = b
        self.a = a


class ColorButton(QtWidgets.QToolButton):

    currentColorChanged = QtCore.pyqtSignal(Color)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._pixmap = QtGui.QPixmap(self.iconSize())
        self.setColor(Color())
        self.clicked.connect(self.on_clicked)

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

    def setColor(self, color):
        self._color = color
        self._pixmap.fill(QtGui.QColor(color.r, color.g, color.b))
        self.setIcon(QtGui.QIcon(self._pixmap))

    @QtCore.pyqtSlot(bool)
    def on_clicked(self, clicked):
        dialog = QtWidgets.QColorDialog()
        dialog.setOptions(
            QtWidgets.QColorDialog.ShowAlphaChannel |
            QtWidgets.QColorDialog.DontUseNativeDialog
        )
        dialog.setCurrentColor(self._to_qcolor(self._color))
        dialog.currentColorChanged.connect(self.on_currentColorChanged)
        dialog.exec_()
        self.setColor(self._from_qcolor(dialog.selectedColor()))

    @QtCore.pyqtSlot(QtGui.QColor)
    def on_currentColorChanged(self, color):
        self.currentColorChanged.emit(self._from_qcolor(color))

