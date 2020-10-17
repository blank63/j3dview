import io
import pkgutil
from PyQt5 import QtCore, QtWidgets, uic
import gx
import views
from views import path_builder as _p
from widgets.view_form import (
    ViewHandler,
    ComboBoxAdaptor,
)


class TexcoordGeneratorListHandler:

    def __init__(self, widget):
        self.widget = widget
        self.material = None
        for value in gx.TEXCOORD:
            self.widget.addItem(value.name)

    def currentTexcoordGeneratorPath(self):
        row = self.widget.currentRow()
        assert row != -1
        return +_p.texcoord_generators[row]

    def currentTexcoordGenerator(self):
        return self.currentTexcoordGeneratorPath().get_value(self.material)

    def setMaterial(self, material):
        if self.material is not None:
            self.material.unregister_listener(self)
        self.material = material
        self.widget.setCurrentRow(-1)
        self.reload()
        self.material.register_listener(self)

    def clear(self):
        if self.material is not None:
            self.material.unregister_listener(self)
        self.material = None
        self.widget.setCurrentRow(-1)

    def reload(self):
        if self.widget.currentRow() == -1 and self.material.texcoord_generator_count > 0:
            self.widget.setCurrentRow(0)
        elif self.widget.currentRow() >= self.material.texcoord_generator_count:
            self.widget.setCurrentRow(self.material.texcoord_generator_count - 1)

        for i in range(self.material.texcoord_generator_count):
            item = self.widget.item(i)
            item.setFlags(item.flags() | QtCore.Qt.ItemIsEnabled)
        for i in range(self.material.texcoord_generator_count, self.widget.count()):
            item = self.widget.item(i)
            item.setFlags(item.flags() & ~QtCore.Qt.ItemIsEnabled)

    def handle_event(self, event, path):
        if isinstance(event, views.ValueChangedEvent):
            if path == +_p.texcoord_generator_count:
                self.reload()


class TexcoordGeneratorDialog(QtWidgets.QDialog):

    commitViewValue = QtCore.pyqtSignal(views.Path, object, object, str)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.ui = uic.loadUi(io.BytesIO(pkgutil.get_data(__package__, 'TexcoordGeneratorDialog.ui')), self)

        for i in range(len(gx.TEXCOORD) + 1):
            self.texcoord_generator_count.addItem(str(i), i)
        for value in gx.TexCoordFunction:
            self.function.addItem(value.name, value)
        for value in gx.TexCoordSource:
            self.source.addItem(value.name, value)
        self.matrix.addItem(gx.IDENTITY.name, gx.IDENTITY)
        for value in gx.TEXMTX:
            self.matrix.addItem(value.name, value)

        self.texcoord_generator_count_handler = ViewHandler()
        self.texcoord_generator_count_handler.add_widget(+_p.texcoord_generator_count, ComboBoxAdaptor(self.texcoord_generator_count), 'Num. Tex. Gens.')
        self.texcoord_generator_count_handler.commitViewValue.connect(self.commitViewValue)

        self.texcoord_generator_list_handler = TexcoordGeneratorListHandler(self.texcoord_generator_list)

        self.texcoord_generator_handler = ViewHandler()
        self.texcoord_generator_handler.add_widget(+_p.function, ComboBoxAdaptor(self.function), 'Function')
        self.texcoord_generator_handler.add_widget(+_p.source, ComboBoxAdaptor(self.source), 'Source')
        self.texcoord_generator_handler.add_widget(+_p.matrix, ComboBoxAdaptor(self.matrix), 'Matrix')
        self.texcoord_generator_handler.commitViewValue.connect(self.on_texcoord_generator_handler_commitViewValue)

        self.setEnabled(False)

    def setMaterial(self, material):
        self.material = material
        self.texcoord_generator_count_handler.setView(material)
        self.texcoord_generator_list_handler.setMaterial(material)
        self.setEnabled(True)

    def clear(self):
        self.texcoord_generator_count_handler.clear()
        self.texcoord_generator_list_handler.clear()
        self.setEnabled(False)

    @QtCore.pyqtSlot(views.Path, object, object, str)
    def on_texcoord_generator_handler_commitViewValue(self, path, old_value, new_value, label):
        texcoord_generator_path = self.texcoord_generator_list_handler.currentTexcoordGeneratorPath()
        self.commitViewValue.emit(texcoord_generator_path + path, old_value, new_value, label)

    @QtCore.pyqtSlot(int)
    def on_texcoord_generator_list_currentRowChanged(self, row):
        if row == -1:
            self.texcoord_generator_handler.clear()
            self.texcoord_generator_handler.setEnabled(False)
            return
        self.texcoord_generator_handler.setView(self.texcoord_generator_list_handler.currentTexcoordGenerator())
        self.texcoord_generator_handler.setEnabled(True)

