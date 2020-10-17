import io
import pkgutil
from PyQt5 import uic
import gx
from views import path_builder as _p
from widgets.view_form import (
    ViewForm,
    LineEditAdaptor,
    ComboBoxAdaptor,
    SpinBoxAdaptor
)


class TextureForm(ViewForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.ui = uic.loadUi(io.BytesIO(pkgutil.get_data(__package__, 'TextureForm.ui')), self)

        for value in gx.WrapMode:
            self.wrap_s.addItem(value.name, value)
            self.wrap_t.addItem(value.name, value)

        for value in gx.FilterMode:
            self.minification_filter.addItem(value.name, value)
        self.magnification_filter.addItem(gx.NEAR.name, gx.NEAR)
        self.magnification_filter.addItem(gx.LINEAR.name, gx.LINEAR)

        self.add_widget(+_p.name, LineEditAdaptor(self.name), 'Name')
        self.add_widget(+_p.wrap_s, ComboBoxAdaptor(self.wrap_s), 'Wrap S')
        self.add_widget(+_p.wrap_t, ComboBoxAdaptor(self.wrap_t), 'Wrap T')
        self.add_widget(+_p.minification_filter, ComboBoxAdaptor(self.minification_filter), 'Min. Filter')
        self.add_widget(+_p.magnification_filter, ComboBoxAdaptor(self.magnification_filter), 'Mag. Filter')
        self.add_widget(+_p.minimum_lod, SpinBoxAdaptor(self.minimum_lod), 'Min. LOD')
        self.add_widget(+_p.maximum_lod, SpinBoxAdaptor(self.maximum_lod), 'max. LOD')
        self.add_widget(+_p.lod_bias, SpinBoxAdaptor(self.lod_bias), 'LOD Bias')
        self.add_widget(+_p.unknown0, SpinBoxAdaptor(self.unknown0), 'Unknown 0')
        self.add_widget(+_p.unknown1, SpinBoxAdaptor(self.unknown1), 'Unknown 1')
        self.add_widget(+_p.unknown2, SpinBoxAdaptor(self.unknown2), 'Unknown 2')

    def setTexture(self, texture):
        self.setView(texture)

        self.image_format.setText(self.view.image_format.name)
        self.image_size.setText(f'{self.view.width} x {self.view.height}')
        self.image_levels.setText(str(len(self.view.images)))
        if self.view.palette is not None:
            self.palette_format.setText(self.view.palette.palette_format.name)
            self.palette_size.setText(str(len(self.view.palette)))
        else:
            self.palette_format.setText('-')
            self.palette_size.setText('-')

    def clear(self):
        super().clear()
        self.image_format.clear()
        self.image_size.clear()
        self.image_levels.clear()
        self.palette_format.clear()
        self.palette_size.clear()

