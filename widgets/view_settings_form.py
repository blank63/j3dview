from PyQt5 import QtWidgets,uic


class ViewSettingsForm(QtWidgets.QWidget):

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)

        self.ui = uic.loadUi('widgets/ViewSettingsForm.ui',self)

    def setViewer(self,viewer):
        self.z_near.bindProperty(viewer,'z_near',viewer.z_near_changed)
        self.z_far.bindProperty(viewer,'z_far',viewer.z_far_changed)
        self.fov.bindProperty(viewer,'fov',viewer.fov_changed)
        self.movement_speed.bindProperty(viewer,'movement_speed',viewer.movement_speed_changed)
        self.rotation_speed.bindProperty(viewer,'rotation_speed',viewer.rotation_speed_changed)
