import io
import pkgutil
from PyQt5 import QtCore, QtWidgets, uic
import gx


class CommitAttributeCommand(QtWidgets.QUndoCommand):

    def __init__(self, view, attribute_name):
        super().__init__(f'Change {attribute_name}')
        self.view = view
        self.attribute_name = attribute_name
        self.old_value = getattr(view.viewed_object, attribute_name)
        self.new_value = getattr(view, attribute_name)

    def redo(self):
        setattr(self.view, self.attribute_name, self.new_value)
        setattr(self.view.viewed_object, self.attribute_name, self.new_value)

    def undo(self):
        setattr(self.view, self.attribute_name, self.old_value)
        setattr(self.view.viewed_object, self.attribute_name, self.old_value)


class TextureForm(QtWidgets.QWidget):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.ui = uic.loadUi(io.BytesIO(pkgutil.get_data(__package__, 'TextureForm.ui')), self)

        self.wrap_s.addEnumItems(gx.WrapMode)
        self.wrap_t.addEnumItems(gx.WrapMode)

        self.minification_filter.addEnumItems(gx.FilterMode)

        self.magnification_filter.addItem(gx.NEAR.name, gx.NEAR)
        self.magnification_filter.addItem(gx.LINEAR.name, gx.LINEAR)

        self.setEnabled(False)

        self.texture = None

    def setTexture(self, texture):
        if self.texture is not None:
            self.texture.unregister_listener(self)
        self.texture = texture
        self.reload()
        self.texture.register_listener(self)
        self.setEnabled(True)

    def receive_event(self, sender, event):
        self.reload()

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

    def commit_attribute(self, attribute_name):
        old_value = getattr(self.texture.viewed_object, attribute_name)
        new_value = getattr(self.texture, attribute_name)
        if new_value == old_value:
            return
        command = CommitAttributeCommand(self.texture, attribute_name)
        self.undo_stack.push(command)

    @QtCore.pyqtSlot(str)
    def on_name_textEdited(self, value):
        self.texture.name = value

    @QtCore.pyqtSlot()
    def on_name_editingFinished(self):
        self.commit_attribute('name')

    @QtCore.pyqtSlot(int)
    def on_wrap_s_activated(self, index):
        self.texture.wrap_s = self.wrap_s.itemData(index)
        self.commit_attribute('wrap_s')

    @QtCore.pyqtSlot(int)
    def on_wrap_t_activated(self, index):
        self.texture.wrap_t = self.wrap_t.itemData(index)
        self.commit_attribute('wrap_t')

    @QtCore.pyqtSlot(int)
    def on_minification_filter_activated(self, index):
        self.texture.minification_filter = self.minification_filter.itemData(index)
        self.commit_attribute('minification_filter')

    @QtCore.pyqtSlot(int)
    def on_magnification_filter_activated(self, index):
        self.texture.magnification_filter = self.magnification_filter.itemData(index)
        self.commit_attribute('magnification_filter')

    @QtCore.pyqtSlot(float)
    def on_minimum_lod_valueChanged(self, value):
        self.texture.minimum_lod = value

    @QtCore.pyqtSlot()
    def on_minimum_lod_editingFinished(self):
        self.commit_attribute('minimum_lod')

    @QtCore.pyqtSlot(float)
    def on_maximum_lod_valueChanged(self, value):
        self.texture.maximum_lod = value

    @QtCore.pyqtSlot()
    def on_maximum_lod_editingFinished(self):
        self.commit_attribute('maximum_lod')

    @QtCore.pyqtSlot(float)
    def on_lod_bias_valueChanged(self, value):
        self.texture.lod_bias = value

    @QtCore.pyqtSlot()
    def on_lod_bias_editingFinished(self):
        self.commit_attribute('lod_bias')

    @QtCore.pyqtSlot(int)
    def on_unknown0_valueChanged(self, value):
        self.texture.unknown0 = value

    @QtCore.pyqtSlot()
    def on_unknown0_editingFinished(self):
        self.commit_attribute('unknown0')

    @QtCore.pyqtSlot(int)
    def on_unknown1_valueChanged(self, value):
        self.texture.unknown1 = value

    @QtCore.pyqtSlot()
    def on_unknown1_editingFinished(self):
        self.commit_attribute('unknown1')

    @QtCore.pyqtSlot(int)
    def on_unknown2_valueChanged(self, value):
        self.texture.unknown2 = value

    @QtCore.pyqtSlot()
    def on_unknown2_editingFinished(self):
        self.commit_attribute('unknown2')

