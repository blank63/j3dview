from PyQt4 import QtCore,QtGui,uic
import gx


class ViewSettingsForm(QtGui.QWidget):

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)

        self.ui = uic.loadUi('ui/ViewSettingsForm.ui',self)

    def setViewer(self,viewer):
        self.z_near.bindProperty(viewer,'z_near',viewer.z_near_changed)
        self.z_far.bindProperty(viewer,'z_far',viewer.z_far_changed)
        self.fov.bindProperty(viewer,'fov',viewer.fov_changed)
        self.movement_speed.bindProperty(viewer,'movement_speed',viewer.movement_speed_changed)
        self.rotation_speed.bindProperty(viewer,'rotation_speed',viewer.rotation_speed_changed)


class TextureForm(QtGui.QWidget):

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)

        self.ui = uic.loadUi('ui/TextureForm.ui',self)

        self.wrap_s.setItems([gx.CLAMP,gx.REPEAT,gx.MIRROR])
        self.wrap_t.setItems([gx.CLAMP,gx.REPEAT,gx.MIRROR])
        self.minification_filter.setItems([gx.NEAR,gx.LINEAR,gx.NEAR_MIP_NEAR,gx.LIN_MIP_NEAR,gx.NEAR_MIP_LIN,gx.LIN_MIP_LIN])
        self.magnification_filter.setItems([gx.NEAR,gx.LINEAR])

    @QtCore.pyqtSlot(object)
    def setTexture(self,texture):
        self.name.bindProperty(texture,'name',texture.name_changed)

        self.image_format.setText(texture.image_format.name)
        self.image_size.setText('{} x {}'.format(texture.width,texture.height))
        self.image_levels.setText(str(len(texture.images)))

        if texture.palette is not None:
            self.palette_format.setText(texture.palette.palette_format.name)
            self.palette_size.setText(str(len(texture.palette)))
        else:
            self.palette_format.setText('-')
            self.palette_size.setText('-')

        self.wrap_s.bindProperty(texture,'wrap_s',texture.wrap_s_changed)
        self.wrap_t.bindProperty(texture,'wrap_t',texture.wrap_t_changed)

        self.minification_filter.bindProperty(texture,'minification_filter',texture.minification_filter_changed)
        self.magnification_filter.bindProperty(texture,'magnification_filter',texture.magnification_filter_changed)

        self.minimum_lod.bindProperty(texture,'minimum_lod',texture.minimum_lod_changed)
        self.maximum_lod.bindProperty(texture,'maximum_lod',texture.maximum_lod_changed)
        self.lod_bias.bindProperty(texture,'lod_bias',texture.lod_bias_changed)

        self.unknown0.bindProperty(texture,'unknown0',texture.unknown0_changed)
        self.unknown1.bindProperty(texture,'unknown1',texture.unknown1_changed)
        self.unknown2.bindProperty(texture,'unknown2',texture.unknown2_changed)

    def setUndoStack(self,undo_stack):
        self.name.setUndoStack(undo_stack)

        self.wrap_s.setUndoStack(undo_stack)
        self.wrap_t.setUndoStack(undo_stack)

        self.minification_filter.setUndoStack(undo_stack)
        self.magnification_filter.setUndoStack(undo_stack)

        self.minimum_lod.setUndoStack(undo_stack)
        self.maximum_lod.setUndoStack(undo_stack)
        self.lod_bias.setUndoStack(undo_stack)

        self.unknown0.setUndoStack(undo_stack)
        self.unknown1.setUndoStack(undo_stack)
        self.unknown2.setUndoStack(undo_stack)

