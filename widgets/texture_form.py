import io
import pkgutil
from PyQt5 import uic
import gx
from views import path_builder as _p
from widgets.view_form import (
    ViewForm,
    EnumDelegate,
    LineEditDelegate,
    SpinBoxDelegate,
    DoubleSpinBoxDelegate
)


class TextureForm(ViewForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ui = uic.loadUi(io.BytesIO(pkgutil.get_data(__package__, 'TextureForm.ui')), self)

        self.add_mapping('Name', +_p.name, 
            self.name, LineEditDelegate())
        self.add_mapping('Wrap S', +_p.wrap_s,
            self.wrap_s, EnumDelegate(gx.WrapMode))
        self.add_mapping('Wrap T', +_p.wrap_t,
            self.wrap_t, EnumDelegate(gx.WrapMode))
        self.add_mapping('Min. Filter', +_p.minification_filter,
            self.minification_filter, EnumDelegate(gx.FilterMode))
        self.add_mapping('Mag. Filter', +_p.magnification_filter,
            self.magnification_filter, EnumDelegate([gx.NEAR, gx.LINEAR]))
        self.add_mapping('Min. LOD', +_p.minimum_lod,
            self.minimum_lod, DoubleSpinBoxDelegate(0, 10))
        self.add_mapping('Max. LOD', +_p.maximum_lod,
            self.maximum_lod, DoubleSpinBoxDelegate(0, 10))
        self.add_mapping('LOD Bias', +_p.lod_bias,
            self.lod_bias, DoubleSpinBoxDelegate(-4, 3.99))
        self.add_mapping('Unknown 0', +_p.unknown0,
            self.unknown0, SpinBoxDelegate(0, 255))
        self.add_mapping('Unknown 1', +_p.unknown1,
            self.unknown1, SpinBoxDelegate(0, 255))
        self.add_mapping('Unknown 2', +_p.unknown2,
            self.unknown2, SpinBoxDelegate(0, 255))

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

