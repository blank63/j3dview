import io
import pkgutil
from PyQt5 import QtCore, QtWidgets, uic


class ViewSettingsForm(QtWidgets.QWidget):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.ui = uic.loadUi(io.BytesIO(pkgutil.get_data(__package__, 'ViewSettingsForm.ui')), self)

        self.viewer = None

    def setViewer(self, viewer):
        self.viewer = viewer
        self.z_near.setValue(self.viewer.z_near)
        self.z_far.setValue(self.viewer.z_far)
        self.movement_speed.setValue(self.viewer.movement_speed)
        self.rotation_speed.setValue(self.viewer.rotation_speed)

    @QtCore.pyqtSlot(float)
    def on_z_near_valueChanged(self, value):
        if self.viewer is None: return
        self.viewer.z_near = value
        self.viewer.projection_matrix_need_update = True

    @QtCore.pyqtSlot(float)
    def on_z_far_valueChanged(self, value):
        if self.viewer is None: return
        self.viewer.z_far = value
        self.viewer.projection_matrix_need_update = True

    @QtCore.pyqtSlot(float)
    def on_movement_speed_valueChanged(self, value):
        if self.viewer is None: return
        self.viewer.movement_speed = value

    @QtCore.pyqtSlot(float)
    def on_rotation_speed_valueChanged(self, value):
        if self.viewer is None: return
        self.viewer.rotation_speed = value

