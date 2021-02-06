import io
import pkgutil
from PyQt5.QtCore import Qt
from PyQt5 import QtWidgets, uic
import gx
from modelview.path import PATH_BUILDER as _p
from modelview.object_model import ItemInsertEvent, ItemRemoveEvent, ObjectModel
from widgets.modelview import (
    DataWidgetMapper,
    DataDelegateMapper,
    CheckBoxDelegate,
    EnumDelegate,
    ItemModelBoxDelegate,
    LineEditDelegate,
    SpinBoxDelegate,
    ColorButtonDelegate
)
from widgets.item_model_adaptor import (
    Entry,
    Item,
    AbstractListItem,
    ItemModelAdaptor
)


_bool = CheckBoxDelegate
_int = SpinBoxDelegate
_enum = EnumDelegate
_str = LineEditDelegate
_color = ColorButtonDelegate
_texture = ItemModelBoxDelegate


class TextureList(ObjectModel):

    def __init__(self, textures):
        super().__init__()
        self.textures = textures
        textures.register_listener(self)

    def __len__(self):
        return len(self.textures) + 1

    def __getitem__(self, index):
        assert index != 0
        return self.textures[index - 1]

    def handle_event(self, event, path):
        if path:
            index = path[0].key
            self.emit_event(event, +_p[index + 1] + path[1:])
            return
        if isinstance(event, ItemInsertEvent):
            self.emit_event(ItemInsertEvent(event.index + 1), path)
            return
        if isinstance(event, ItemRemoveEvent):
            self.emit_event(ItemRemoveEvent(event.index + 1), path)
            return
        self.emit_event(event, path)


class TextureListItem(AbstractListItem):

    def __init__(self):
        super().__init__(column_count=1)
        self.list_path = +_p

    def create_child(self, index):
        if index == 0:
            return Item([Entry(
                data='None',
                role_data={Qt.UserRole: None}
            )])
        return Item([Entry(
            path=+_p[index].name,
            role_paths={Qt.UserRole: +_p[index]}
        )])


class MaterialForm(QtWidgets.QWidget):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ui = uic.loadUi(io.BytesIO(pkgutil.get_data(__package__, 'MaterialForm.ui')), self)

        self.texture_list_adaptor = ItemModelAdaptor(root_item=TextureListItem())
        self.texture0.setModel(self.texture_list_adaptor)
        self.texture1.setModel(self.texture_list_adaptor)
        self.texture2.setModel(self.texture_list_adaptor)
        self.texture3.setModel(self.texture_list_adaptor)
        self.texture4.setModel(self.texture_list_adaptor)
        self.texture5.setModel(self.texture_list_adaptor)
        self.texture6.setModel(self.texture_list_adaptor)
        self.texture7.setModel(self.texture_list_adaptor)

        self.material = None
        self.material_adaptor = ItemModelAdaptor(column_count=1)
        self.mapper = DataWidgetMapper(orientation=Qt.Vertical)
        self.mapper.setModel(self.material_adaptor)
        self.mapper_delegate = DataDelegateMapper()
        self.mapper.setItemDelegate(self.mapper_delegate)

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

        self.setEnabled(False)

    def add_mapping(self, label, path, widget, delegate):
        section = self.material_adaptor.top_level_item_count()
        item = Item([Entry(path=path, label=label, editable=True)])
        self.material_adaptor.add_top_level_item(item)
        self.mapper.addMapping(widget, section)
        self.mapper_delegate.addMapping(delegate, section)
        delegate.initEditor(widget)

    def setUndoStack(self, undo_stack):
        self.material_adaptor.setUndoStack(undo_stack)

    def setTextures(self, textures):
        self.texture_list_adaptor.setObjectModel(TextureList(textures))

    def setMaterial(self, material):
        self.material = material
        self.material_adaptor.setObjectModel(material)
        self.setEnabled(True)

    def clear(self):
        self.material = None
        self.material_adaptor.setObjectModel(None)
        self.texture_list_adaptor.setObjectModel(None)
        self.setEnabled(False)

