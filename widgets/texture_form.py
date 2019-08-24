import io
import pkgutil
from PyQt5 import QtCore, QtWidgets, uic
import gx


class TextureForm(QtWidgets.QWidget):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.ui = uic.loadUi(io.BytesIO(pkgutil.get_data(__package__, 'TextureForm.ui')), self)

        self.wrap_s.addItem(gx.CLAMP.name, gx.CLAMP)
        self.wrap_s.addItem(gx.REPEAT.name, gx.REPEAT)
        self.wrap_s.addItem(gx.MIRROR.name, gx.MIRROR)

        self.wrap_t.addItem(gx.CLAMP.name, gx.CLAMP)
        self.wrap_t.addItem(gx.REPEAT.name, gx.REPEAT)
        self.wrap_t.addItem(gx.MIRROR.name, gx.MIRROR)

        self.minification_filter.addItem(gx.NEAR.name, gx.NEAR)
        self.minification_filter.addItem(gx.LINEAR.name, gx.LINEAR)
        self.minification_filter.addItem(gx.NEAR_MIP_NEAR.name, gx.NEAR_MIP_NEAR)
        self.minification_filter.addItem(gx.LIN_MIP_NEAR.name, gx.LIN_MIP_NEAR)
        self.minification_filter.addItem(gx.NEAR_MIP_LIN.name, gx.NEAR_MIP_LIN)
        self.minification_filter.addItem(gx.LIN_MIP_LIN.name, gx.LIN_MIP_LIN)

        self.magnification_filter.addItem(gx.NEAR.name, gx.NEAR)
        self.magnification_filter.addItem(gx.LINEAR.name, gx.LINEAR)

        self.texture = None

    def setTexture(self, texture):
        if self.texture is not None:
            self.texture.unregister(self.reload)
        self.texture = texture
        self.reload()
        self.texture.register(self.reload)

    def reload(self):
        self.name.setText(self.texture.name)

        self.image_format.setText(self.texture.image_format.name)
        self.image_size.setText('{} x {}'.format(self.texture.width, self.texture.height))
        self.image_levels.setText(str(len(self.texture.images)))

        if self.texture.palette is not None:
            self.palette_format.setText(self.texture.palette.palette_format.name)
            self.palette_size.setText(str(len(self.texture.palette)))
        else:
            self.palette_format.setText('-')
            self.palette_size.setText('-')

        self.wrap_s.setCurrentData(self.texture.wrap_s)
        self.wrap_t.setCurrentData(self.texture.wrap_t)

        self.minification_filter.setCurrentData(self.texture.minification_filter)
        self.magnification_filter.setCurrentData(self.texture.magnification_filter)

        self.minimum_lod.setValue(self.texture.minimum_lod)
        self.maximum_lod.setValue(self.texture.maximum_lod)
        self.lod_bias.setValue(self.texture.lod_bias)

        self.unknown0.setValue(self.texture.unknown0)
        self.unknown1.setValue(self.texture.unknown1)
        self.unknown2.setValue(self.texture.unknown2)

    @QtCore.pyqtSlot(str)
    def on_name_textEdited(self, value):
        if self.texture is None: return
        self.texture.name = value

    @QtCore.pyqtSlot()
    def on_name_editingFinished(self):
        if self.texture is None: return
        self.texture.commit()

    @QtCore.pyqtSlot(int)
    def on_wrap_s_activated(self, index):
        if self.texture is None: return
        self.texture.wrap_s = self.wrap_s.itemData(index)
        self.texture.commit()

    @QtCore.pyqtSlot(int)
    def on_wrap_t_activated(self, index):
        if self.texture is None: return
        self.texture.wrap_t = self.wrap_t.itemData(index)
        self.texture.commit()

    @QtCore.pyqtSlot(int)
    def on_minification_filter_activated(self, index):
        if self.texture is None: return
        self.texture.minification_filter = self.minification_filter.itemData(index)
        self.texture.commit()

    @QtCore.pyqtSlot(int)
    def on_magnification_filter_activated(self, index):
        if self.texture is None: return
        self.texture.magnification_filter = self.magnification_filter.itemData(index)
        self.texture.commit()

    @QtCore.pyqtSlot(float)
    def on_minimum_lod_valueChanged(self, value):
        if self.texture is None: return
        self.texture.minimum_lod = value
        self.texture.gl_sampler_invalidate()

    @QtCore.pyqtSlot()
    def on_minimum_lod_editingFinished(self, value):
        if self.texture is None: return
        self.texture.commit()

    @QtCore.pyqtSlot(float)
    def on_maximum_lod_valueChanged(self, value):
        if self.texture is None: return
        self.texture.maximum_lod = value
        self.texture.gl_sampler_invalidate()

    @QtCore.pyqtSlot()
    def on_maximum_lod_editingFinished(self, value):
        if self.texture is None: return
        self.texture.commit()

    @QtCore.pyqtSlot(float)
    def on_lod_bias_valueChanged(self, value):
        if self.texture is None: return
        self.texture.lod_bias = value
        self.texture.gl_sampler_invalidate()

    @QtCore.pyqtSlot()
    def on_lod_bias_editingFinished(self, value):
        if self.texture is None: return
        self.texture.commit()

    @QtCore.pyqtSlot(int)
    def on_unknown0_valueChanged(self, value):
        if self.texture is None: return
        self.texture.unknown0 = value

    @QtCore.pyqtSlot()
    def on_unknown0_editingFinished(self, value):
        if self.texture is None: return
        self.texture.commit()

    @QtCore.pyqtSlot(int)
    def on_unknown1_valueChanged(self, value):
        if self.texture is None: return
        self.texture.unknown1 = value

    @QtCore.pyqtSlot()
    def on_unknown1_editingFinished(self, value):
        if self.texture is None: return
        self.texture.commit()

    @QtCore.pyqtSlot(int)
    def on_unknown2_valueChanged(self, value):
        if self.texture is None: return
        self.texture.unknown2 = value

    @QtCore.pyqtSlot()
    def on_unknown2_editingFinished(self, value):
        if self.texture is None: return
        self.texture.commit()

