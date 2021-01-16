import io
import pkgutil
from PyQt5 import QtCore, QtGui, uic
import gx
from modelview.path import PATH_BUILDER as _p
from modelview.object_model import ItemInsertEvent, ItemRemoveEvent
from widgets.view_form import (
    Item,
    ItemModelAdaptor,
    ViewForm,
    CheckBoxDelegate,
    ItemModelBoxDelegate,
    EnumDelegate,
    LineEditDelegate,
    SpinBoxDelegate,
    ColorButtonDelegate
)
from widgets.advanced_material_dialog import AdvancedMaterialDialog


_bool = CheckBoxDelegate
_int = SpinBoxDelegate
_enum = EnumDelegate
_str = LineEditDelegate
_color = ColorButtonDelegate
_texture = ItemModelBoxDelegate


class NoneItem(Item):

    @property
    def column_count(self):
        return 1

    def get_flags(self, column):
        return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

    def get_data(self, column, role):
        if role == QtCore.Qt.DisplayRole:
            return 'None'
        if role == QtCore.Qt.UserRole:
            return None
        return QtCore.QVariant()


class TextureItem(Item):

    def __init__(self, index):
        super().__init__()
        self.index = index
        self.triggers = frozenset((+_p[index].name,))

    @property
    def texture(self):
        return self.model.view[self.index]

    @property
    def column_count(self):
        return 1

    def get_flags(self, column):
        return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

    def get_data(self, column, role):
        if role == QtCore.Qt.DisplayRole:
            return self.texture.name
        if role == QtCore.Qt.UserRole:
            return self.texture
        return QtCore.QVariant()

    def handle_event(self, event, path):
        self.model.item_data_changed(self)


class TextureListAdaptor(ItemModelAdaptor):

    def __init__(self, textures):
        super().__init__(textures)
        self.set_header_labels(['Value'])
        self.add_item(NoneItem())
        for i in range(len(textures)):
            self.add_item(TextureItem(i))

    def handle_event(self, event, path):
        if path.match(+_p):
            if isinstance(event, ItemInsertEvent):
                row = event.index + 1
                texture_index = len(self.view) - 1
                self.beginInsertRows(QtCore.QModelIndex(), row, row)
                self.add_item(TextureItem(texture_index))
                self.endInsertRows()
            elif isinstance(event, ItemRemoveEvent):
                row = event.index + 1
                self.beginRemoveRows(QtCore.QModelIndex(), row, row)
                self.take_item(self.rowCount() - 1)
                self.endRemoveRows()
        super().handle_event(event, path)


class MaterialForm(ViewForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ui = uic.loadUi(io.BytesIO(pkgutil.get_data(__package__, 'MaterialForm.ui')), self)

        self.add_mapping('Name', +_p.name, self.name, _str())
        self.add_mapping('Unknown 0', +_p.unknown0, self.unknown0, _int(min=0, max=255))
        self.add_mapping('Cull Mode', +_p.cull_mode, self.cull_mode, _enum(gx.CullMode))
        self.add_mapping('Dither', +_p.dither, self.dither, _bool())

        self.add_mapping('Mat. Color 0', +_p.channels[0].material_color, self.material_color0, _color())
        self.add_mapping('Amb. Color 0', +_p.channels[0].ambient_color, self.ambient_color0, _color())
        self.add_mapping('Mat. Color 1', +_p.channels[1].material_color, self.material_color1, _color())
        self.add_mapping('Amb. Color 1', +_p.channels[1].ambient_color, self.ambient_color1, _color())

        self.add_mapping('Texture 0', +_p.textures[0], self.texture0, _texture())
        self.add_mapping('Texture 1', +_p.textures[1], self.texture1, _texture())
        self.add_mapping('Texture 2', +_p.textures[2], self.texture2, _texture())
        self.add_mapping('Texture 3', +_p.textures[3], self.texture3, _texture())
        self.add_mapping('Texture 4', +_p.textures[4], self.texture4, _texture())
        self.add_mapping('Texture 5', +_p.textures[5], self.texture5, _texture())
        self.add_mapping('Texture 6', +_p.textures[6], self.texture6, _texture())
        self.add_mapping('Texture 7', +_p.textures[7], self.texture7, _texture())

        #TODO support for S10 TEV colors
        self.add_mapping('TEV Prev', +_p.tev_color_previous, self.tev_color_previous, _color())
        self.add_mapping('TEV Reg. 0', +_p.tev_colors[0], self.tev_color0, _color())
        self.add_mapping('TEV Reg. 1', +_p.tev_colors[1], self.tev_color1, _color())
        self.add_mapping('TEV Reg. 2', +_p.tev_colors[2], self.tev_color2, _color())
        self.add_mapping('KColor 0', +_p.kcolors[0], self.kcolor0, _color())
        self.add_mapping('KColor 1', +_p.kcolors[1], self.kcolor1, _color())
        self.add_mapping('KColor 2', +_p.kcolors[2], self.kcolor2, _color())
        self.add_mapping('KColor 3', +_p.kcolors[3], self.kcolor3, _color())

        self.add_mapping('Function 0', +_p.alpha_test.function0, self.alpha_test_function0, _enum(gx.CompareFunction))
        self.add_mapping('Reference 0', +_p.alpha_test.reference0, self.alpha_test_reference0, _int(min=0, max=255))
        self.add_mapping('Function 1', +_p.alpha_test.function1, self.alpha_test_function1, _enum(gx.CompareFunction))
        self.add_mapping('Reference 1', +_p.alpha_test.reference1, self.alpha_test_reference1, _int(min=0, max=255))
        self.add_mapping('Operator', +_p.alpha_test.operator, self.alpha_test_operator, _enum(gx.AlphaOperator))

        self.add_mapping('Enable', +_p.depth_mode.enable, self.depth_mode_enable, _bool())
        self.add_mapping('Test Early', +_p.depth_test_early, self.depth_mode_test_early, _bool())
        self.add_mapping('Function', +_p.depth_mode.function, self.depth_mode_function, _enum(gx.CompareFunction))
        self.add_mapping('Update Enable', +_p.depth_mode.update_enable, self.depth_mode_update_enable, _bool())

        self.add_mapping('Function', +_p.blend_mode.function, self.blend_mode_function, _enum(gx.BlendFunction))
        self.add_mapping('Src. Factor', +_p.blend_mode.source_factor, self.blend_mode_source_factor, _enum(gx.BlendSourceFactor))
        self.add_mapping('Dst. Factor', +_p.blend_mode.destination_factor, self.blend_mode_destination_factor, _enum(gx.BlendDestinationFactor))
        self.add_mapping('Logic Op.', +_p.blend_mode.logical_operation, self.blend_mode_logical_operation, _enum(gx.LogicalOperation))

        self.advanced_material_dialog = AdvancedMaterialDialog()
        self.advanced_material_dialog.commitViewValue.connect(self.commitViewValue.emit)
        self.advanced_material_dialog.finished.connect(self.on_advanced_material_dialog_finished)

    def setTextures(self, textures):
        adaptor = TextureListAdaptor(textures)
        self.texture0.setModel(adaptor)
        self.texture1.setModel(adaptor)
        self.texture2.setModel(adaptor)
        self.texture3.setModel(adaptor)
        self.texture4.setModel(adaptor)
        self.texture5.setModel(adaptor)
        self.texture6.setModel(adaptor)
        self.texture7.setModel(adaptor)

    def setMaterial(self, material):
        self.setView(material)
        if not self.advanced_material_dialog.isHidden():
            self.advanced_material_dialog.setMaterial(material)

    def clear(self):
        super().clear()
        empty_model = QtGui.QStandardItemModel()
        self.texture0.setModel(empty_model)
        self.texture1.setModel(empty_model)
        self.texture2.setModel(empty_model)
        self.texture3.setModel(empty_model)
        self.texture4.setModel(empty_model)
        self.texture5.setModel(empty_model)
        self.texture6.setModel(empty_model)
        self.texture7.setModel(empty_model)
        self.advanced_material_dialog.clear()

    @QtCore.pyqtSlot(bool)
    def on_advanced_button_clicked(self, checked):
        self.advanced_material_dialog.setMaterial(self.view)
        self.advanced_material_dialog.show()
        self.advanced_material_dialog.raise_()
        self.advanced_material_dialog.activateWindow()

    @QtCore.pyqtSlot(int)
    def on_advanced_material_dialog_finished(self, result):
        self.advanced_material_dialog.clear()

