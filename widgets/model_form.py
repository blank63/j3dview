import io
import pkgutil
from PyQt5 import QtWidgets, uic


class ModelForm(QtWidgets.QWidget):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ui = uic.loadUi(io.BytesIO(pkgutil.get_data(__package__, 'ModelForm.ui')), self)
        self.model = None
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

        self.setEnabled(True)

    def clear(self):
        self.model = None
        self.subversion.clear()
        self.unknown0.clear()
        self.setEnabled(False)

