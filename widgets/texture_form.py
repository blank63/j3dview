import io
import pkgutil
from PyQt5.QtCore import Qt
from PyQt5 import QtWidgets, uic
import gx
from modelview.path import PATH_BUILDER as _p
from widgets.modelview import (
    DataWidgetMapper,
    DataDelegateMapper,
    EnumDelegate,
    LineEditDelegate,
    SpinBoxDelegate,
    DoubleSpinBoxDelegate
)
from widgets.item_model_adaptor import (
    Entry,
    Item,
    ItemModelAdaptor
)


_int = SpinBoxDelegate
_float = DoubleSpinBoxDelegate
_enum = EnumDelegate
_str = LineEditDelegate


class TextureForm(QtWidgets.QWidget):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ui = uic.loadUi(io.BytesIO(pkgutil.get_data(__package__, 'TextureForm.ui')), self)

        self.texture_adaptor = ItemModelAdaptor(column_count=1)
        self.mapper = DataWidgetMapper(orientation=Qt.Vertical)
        self.mapper.setModel(self.texture_adaptor)
        self.mapper_delegate = DataDelegateMapper()
        self.mapper.setItemDelegate(self.mapper_delegate)

        self.add_mapping('Name', +_p.name, self.name, _str())
        self.add_mapping('Wrap S', +_p.wrap_s, self.wrap_s, _enum(gx.WrapMode))
        self.add_mapping('Wrap T', +_p.wrap_t, self.wrap_t, _enum(gx.WrapMode))
        self.add_mapping('Min. Filter', +_p.minification_filter, self.minification_filter, _enum(gx.FilterMode))
        self.add_mapping('Mag. Filter', +_p.magnification_filter, self.magnification_filter, _enum([gx.NEAR, gx.LINEAR]))
        self.add_mapping('Min. LOD', +_p.minimum_lod, self.minimum_lod, _float(min=0, max=10))
        self.add_mapping('Max. LOD', +_p.maximum_lod, self.maximum_lod, _float(min=0, max=10))
        self.add_mapping('LOD Bias', +_p.lod_bias, self.lod_bias, _float(min=-4, max=3.99))
        self.add_mapping('Unknown 0', +_p.unknown0, self.unknown0, _int(min=0, max=255))
        self.add_mapping('Unknown 1', +_p.unknown1, self.unknown1, _int(min=0, max=255))
        self.add_mapping('Unknown 2', +_p.unknown2, self.unknown2, _int(min=0, max=255))

        self.setEnabled(False)

    def add_mapping(self, label, path, widget, delegate):
        section = self.texture_adaptor.top_level_item_count()
        item = Item([Entry(path=path, label=label, editable=True)])
        self.texture_adaptor.add_top_level_item(item)
        self.mapper.addMapping(widget, section)
        self.mapper_delegate.addMapping(delegate, section)
        delegate.initEditor(widget)

    def setUndoStack(self, undo_stack):
        self.texture_adaptor.setUndoStack(undo_stack)

    def setTexture(self, texture):
        self.texture_adaptor.setObjectModel(texture)
        self.image_format.setText(texture.image_format.name)
        self.image_size.setText(f'{texture.width} x {texture.height}')
        self.image_levels.setText(str(len(texture.images)))
        if texture.palette is not None:
            self.palette_format.setText(texture.palette.palette_format.name)
            self.palette_size.setText(str(len(texture.palette)))
        else:
            self.palette_format.setText('-')
            self.palette_size.setText('-')
        self.setEnabled(True)

    def clear(self):
        self.texture_adaptor.setObjectModel(None)
        self.image_format.clear()
        self.image_size.clear()
        self.image_levels.clear()
        self.palette_format.clear()
        self.palette_size.clear()
        self.setEnabled(False)

