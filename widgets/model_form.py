import io
import pkgutil
from PyQt5 import QtWidgets, uic


class ModelForm(QtWidgets.QWidget):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ui = uic.loadUi(io.BytesIO(pkgutil.get_data(__package__, 'ModelForm.ui')), self)

    def setModel(self, model):
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
        self.subversion.clear()
        self.unknown0.clear()
        self.vertex_array_info.clear()

