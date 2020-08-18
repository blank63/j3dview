from PyQt5 import QtWidgets
import gl


class ComboBox(QtWidgets.QComboBox):

    def setCurrentData(self, value):
        index = self.findData(value)
        assert index != -1
        self.setCurrentIndex(index)

    def addEnumItems(self, enum_type):
        for value in enum_type:
            self.addItem(value.name, value)


class OpenGLWidget(QtWidgets.QOpenGLWidget, gl.ResourceOwner):

    def __init__(self, *args, **kwargs):
        super(QtWidgets.QOpenGLWidget, self).__init__(*args, **kwargs)
        super(gl.ResourceOwner, self).__init__()
        self.destroyed.connect(self.gl_delete)

