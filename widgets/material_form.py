import io
import pkgutil
from PyQt5 import QtCore, QtWidgets, uic
import gx
import views
from views import path_builder as _p
from widgets.view_form import (
    ViewForm,
    LineEditAdaptor,
    ComboBoxAdaptor,
    SpinBoxAdaptor,
    CheckBoxAdaptor,
    ColorButtonAdaptor
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

        for value in gx.CullMode:
            self.cull_mode.addItem(value.name, value)

        for value in gx.CompareFunction:
            self.alpha_test_function0.addItem(value.name, value)
            self.alpha_test_function1.addItem(value.name, value)
        for value in gx.AlphaOperator:
            self.alpha_test_operator.addItem(value.name, value)

        for value in gx.CompareFunction:
            self.depth_mode_function.addItem(value.name, value)

        for value in gx.BlendFunction:
            self.blend_mode_function.addItem(value.name, value)
        for value in gx.BlendSourceFactor:
            self.blend_mode_source_factor.addItem(value.name, value)
        for value in gx.BlendDestinationFactor:
            self.blend_mode_destination_factor.addItem(value.name, value)
        for value in gx.LogicalOperation:
            self.blend_mode_logical_operation.addItem(value.name, value)

        self.add_widget(+_p.name, LineEditAdaptor(self.name), 'Name')
        self.add_widget(+_p.unknown0, SpinBoxAdaptor(self.unknown0), 'Unknown 0')
        self.add_widget(+_p.cull_mode, ComboBoxAdaptor(self.cull_mode), 'Cull Mode')
        self.add_widget(+_p.dither, CheckBoxAdaptor(self.dither), 'Dither')

        self.add_widget(+_p.channels[0].material_color, ColorButtonAdaptor(self.material_color0), 'Mat. Color 0')
        self.add_widget(+_p.channels[0].ambient_color, ColorButtonAdaptor(self.ambient_color0), 'Amb. Color 0')
        self.add_widget(+_p.channels[1].material_color, ColorButtonAdaptor(self.material_color1), 'Mat. Color 1')
        self.add_widget(+_p.channels[1].ambient_color, ColorButtonAdaptor(self.ambient_color1), 'Amb. Color 1')

        self.add_widget(+_p.texture_indices[0], ComboBoxAdaptor(self.texture0), 'Texture 0')
        self.add_widget(+_p.texture_indices[1], ComboBoxAdaptor(self.texture1), 'Texture 1')
        self.add_widget(+_p.texture_indices[2], ComboBoxAdaptor(self.texture2), 'Texture 2')
        self.add_widget(+_p.texture_indices[3], ComboBoxAdaptor(self.texture3), 'Texture 3')
        self.add_widget(+_p.texture_indices[4], ComboBoxAdaptor(self.texture4), 'Texture 4')
        self.add_widget(+_p.texture_indices[5], ComboBoxAdaptor(self.texture5), 'Texture 5')
        self.add_widget(+_p.texture_indices[6], ComboBoxAdaptor(self.texture6), 'Texture 6')
        self.add_widget(+_p.texture_indices[7], ComboBoxAdaptor(self.texture6), 'Texture 7')

        #TODO support for S10 TEV colors
        self.add_widget(+_p.tev_color_previous, ColorButtonAdaptor(self.tev_color_previous), 'TEV Prev')
        self.add_widget(+_p.tev_colors[0], ColorButtonAdaptor(self.tev_color0), 'TEV Reg. 0')
        self.add_widget(+_p.tev_colors[1], ColorButtonAdaptor(self.tev_color1), 'TEV Reg. 1')
        self.add_widget(+_p.tev_colors[2], ColorButtonAdaptor(self.tev_color2), 'TEV Reg. 2')
        self.add_widget(+_p.kcolors[0], ColorButtonAdaptor(self.kcolor0), 'KColor 0')
        self.add_widget(+_p.kcolors[1], ColorButtonAdaptor(self.kcolor1), 'KColor 1')
        self.add_widget(+_p.kcolors[2], ColorButtonAdaptor(self.kcolor2), 'KColor 2')
        self.add_widget(+_p.kcolors[3], ColorButtonAdaptor(self.kcolor3), 'KColor 3')

        self.add_widget(+_p.alpha_test.function0, ComboBoxAdaptor(self.alpha_test_function0), 'Alpha Test Function 0')
        self.add_widget(+_p.alpha_test.reference0, SpinBoxAdaptor(self.alpha_test_reference0), 'Alpha Test Reference 0')
        self.add_widget(+_p.alpha_test.function1, ComboBoxAdaptor(self.alpha_test_function1), 'Alpha Test Function 1')
        self.add_widget(+_p.alpha_test.reference1, SpinBoxAdaptor(self.alpha_test_reference1), 'Alpha Test Reference 1')
        self.add_widget(+_p.alpha_test.operator, ComboBoxAdaptor(self.alpha_test_operator), 'Alpha Test Operator')

        self.add_widget(+_p.depth_mode.enable, CheckBoxAdaptor(self.depth_mode_enable), 'Depth Enable')
        self.add_widget(+_p.depth_test_early, CheckBoxAdaptor(self.depth_mode_test_early), 'Depth Test Early')
        self.add_widget(+_p.depth_mode.function, ComboBoxAdaptor(self.depth_mode_function), 'Depth Function')
        self.add_widget(+_p.depth_mode.update_enable, CheckBoxAdaptor(self.depth_mode_update_enable), 'Depth Update Enable')

        self.add_widget(+_p.blend_mode.function, ComboBoxAdaptor(self.blend_mode_function), 'Blend Function')
        self.add_widget(+_p.blend_mode.source_factor, ComboBoxAdaptor(self.blend_mode_source_factor), 'Blend Src. Factor')
        self.add_widget(+_p.blend_mode.destination_factor, ComboBoxAdaptor(self.blend_mode_destination_factor), 'Blend Dst. Factor')
        self.add_widget(+_p.blend_mode.logical_operation, ComboBoxAdaptor(self.blend_mode_logical_operation), 'Blend Logical Op')

        self.advanced_material_dialog = AdvancedMaterialDialog()

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

