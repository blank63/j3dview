import io
import pkgutil
from PyQt5 import QtCore, QtWidgets, uic
import gx
import views
from views import path_builder as _p
from widgets.view_form import (
    ViewForm,
    CheckBoxDelegate,
    ComboBoxDelegate,
    EnumDelegate,
    LineEditDelegate,
    SpinBoxDelegate,
    ColorButtonDelegate
)
from widgets.advanced_material_dialog import AdvancedMaterialDialog


class TextureBoxHandler:

    def __init__(self, widget):
        self.widget = widget
        self.textures = None

    def setTextures(self, textures):
        if self.textures is not None:
            self.textures.unregister_listener(self)
        self.textures = textures
        self.widget.clear()
        self.widget.addItem('None', None)
        for i, texture in enumerate(textures):
            self.widget.addItem(texture.name, i)
        self.textures.register_listener(self)

    def clear(self):
        if self.textures is not None:
            self.textures.unregister_listener(self)
        self.textures = None
        self.widget.clear()

    def handle_event(self, event, path):
        if isinstance(event, views.ValueChangedEvent):
            if path.match(+_p[...]) or path.match(+_p[...].name):
                index = path[0].key
                texture = self.textures[index]
                item = self.widget.findData(index)
                self.widget.setItemText(item, texture.name)


class MaterialForm(ViewForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ui = uic.loadUi(io.BytesIO(pkgutil.get_data(__package__, 'MaterialForm.ui')), self)

        self.texture_template = QtWidgets.QComboBox()
        self.texture_template_handler = TextureBoxHandler(self.texture_template)
        self.texture0.setModel(self.texture_template.model())
        self.texture1.setModel(self.texture_template.model())
        self.texture2.setModel(self.texture_template.model())
        self.texture3.setModel(self.texture_template.model())
        self.texture4.setModel(self.texture_template.model())
        self.texture5.setModel(self.texture_template.model())
        self.texture6.setModel(self.texture_template.model())
        self.texture7.setModel(self.texture_template.model())

        self.add_mapping('Name', +_p.name,
            self.name, LineEditDelegate())
        self.add_mapping('Unknown 0', +_p.unknown0,
            self.unknown0, SpinBoxDelegate(0, 255))
        self.add_mapping('Cull Mode', +_p.cull_mode,
            self.cull_mode, EnumDelegate(gx.CullMode))
        self.add_mapping('Dither', +_p.dither,
            self.dither, CheckBoxDelegate())

        self.add_mapping('Mat. Color 0', +_p.channels[0].material_color,
            self.material_color0, ColorButtonDelegate())
        self.add_mapping('Amb. Color 0', +_p.channels[0].ambient_color,
            self.ambient_color0, ColorButtonDelegate())
        self.add_mapping('Mat. Color 1', +_p.channels[1].material_color,
            self.material_color1, ColorButtonDelegate())
        self.add_mapping('Amb. Color 1', +_p.channels[1].ambient_color,
            self.ambient_color1, ColorButtonDelegate())

        self.add_mapping('Texture 0', +_p.texture_indices[0],
            self.texture0, ComboBoxDelegate())
        self.add_mapping('Texture 1', +_p.texture_indices[1],
            self.texture1, ComboBoxDelegate())
        self.add_mapping('Texture 2', +_p.texture_indices[2],
            self.texture2, ComboBoxDelegate())
        self.add_mapping('Texture 3', +_p.texture_indices[3],
            self.texture3, ComboBoxDelegate())
        self.add_mapping('Texture 4', +_p.texture_indices[4],
            self.texture4, ComboBoxDelegate())
        self.add_mapping('Texture 5', +_p.texture_indices[5],
            self.texture5, ComboBoxDelegate())
        self.add_mapping('Texture 6', +_p.texture_indices[6],
            self.texture6, ComboBoxDelegate())
        self.add_mapping('Texture 7', +_p.texture_indices[7],
            self.texture7, ComboBoxDelegate())

        #TODO support for S10 TEV colors
        self.add_mapping('TEV Prev', +_p.tev_color_previous,
            self.tev_color_previous, ColorButtonDelegate())
        self.add_mapping('TEV Reg. 0', +_p.tev_colors[0],
            self.tev_color0, ColorButtonDelegate())
        self.add_mapping('TEV Reg. 1', +_p.tev_colors[1],
            self.tev_color1, ColorButtonDelegate())
        self.add_mapping('TEV Reg. 2', +_p.tev_colors[2],
            self.tev_color2, ColorButtonDelegate())
        self.add_mapping('KColor 0', +_p.kcolors[0],
            self.kcolor0, ColorButtonDelegate())
        self.add_mapping('KColor 1', +_p.kcolors[1],
            self.kcolor1, ColorButtonDelegate())
        self.add_mapping('KColor 2', +_p.kcolors[2],
            self.kcolor2, ColorButtonDelegate())
        self.add_mapping('KColor 3', +_p.kcolors[3],
            self.kcolor3, ColorButtonDelegate())

        self.add_mapping('Function 0', +_p.alpha_test.function0,
            self.alpha_test_function0, EnumDelegate(gx.CompareFunction))
        self.add_mapping('Reference 0', +_p.alpha_test.reference0,
            self.alpha_test_reference0, SpinBoxDelegate(0, 255))
        self.add_mapping('Function 1', +_p.alpha_test.function1,
            self.alpha_test_function1, EnumDelegate(gx.CompareFunction))
        self.add_mapping('Reference 1', +_p.alpha_test.reference1,
            self.alpha_test_reference1, SpinBoxDelegate(0, 255))
        self.add_mapping('Operator', +_p.alpha_test.operator,
            self.alpha_test_operator, EnumDelegate(gx.AlphaOperator))

        self.add_mapping('Enable', +_p.depth_mode.enable,
            self.depth_mode_enable, CheckBoxDelegate())
        self.add_mapping('Test Early', +_p.depth_test_early,
            self.depth_mode_test_early, CheckBoxDelegate())
        self.add_mapping('Function', +_p.depth_mode.function,
            self.depth_mode_function, EnumDelegate(gx.CompareFunction))
        self.add_mapping('Update Enable', +_p.depth_mode.update_enable,
            self.depth_mode_update_enable, CheckBoxDelegate())

        self.add_mapping('Function', +_p.blend_mode.function,
            self.blend_mode_function, EnumDelegate(gx.BlendFunction))
        self.add_mapping('Src. Factor', +_p.blend_mode.source_factor,
            self.blend_mode_source_factor, EnumDelegate(gx.BlendSourceFactor))
        self.add_mapping('Dst. Factor', +_p.blend_mode.destination_factor,
            self.blend_mode_destination_factor, EnumDelegate(gx.BlendDestinationFactor))
        self.add_mapping('Logic Op.', +_p.blend_mode.logical_operation,
            self.blend_mode_logical_operation, EnumDelegate(gx.LogicalOperation))

        self.advanced_material_dialog = AdvancedMaterialDialog()
        self.advanced_material_dialog.commitViewValue.connect(self.commitViewValue.emit)

    def setTextures(self, textures):
        self.texture_template_handler.setTextures(textures)

    def setMaterial(self, material):
        self.setView(material)
        self.advanced_material_dialog.setMaterial(material)

    def clear(self):
        super().clear()
        self.texture_template_handler.clear()
        self.advanced_material_dialog.clear()

    @QtCore.pyqtSlot(bool)
    def on_advanced_button_clicked(self, checked):
        self.advanced_material_dialog.show()
        self.advanced_material_dialog.raise_()
        self.advanced_material_dialog.activateWindow()

