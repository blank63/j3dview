import io
import pkgutil
import functools
from PyQt5 import QtCore, QtWidgets, uic
import gx
import views
from views import path_builder as _p
from widgets.view_form import (
    ViewHandler,
    WidgetAdaptor,
    ComboBoxAdaptor,
    CheckBoxAdaptor
)


class LightMaskAdaptor(WidgetAdaptor):

    def __init__(self, widgets):
        super().__init__()
        self.widgets = widgets
        for i, widget in enumerate(self.widgets):
            widget.clicked.connect(functools.partial(self.on_clicked, i))

    def setEnabled(self, value):
        for widget in self.widgets:
            widget.setEnabled(value)

    def update_widget(self, value):
        for i, widget in enumerate(self.widgets):
            widget.setChecked(value & (1 << i))

    def clear_widget(self):
        for widget in self.widgets:
            widget.setChecked(False)

    def on_clicked(self, index, value):
        if value:
            self.commit(self.current_value | (1 << index))
        else:
            self.commit(self.current_value & ~(1 << index))


class LightingModeListHandler:

    def __init__(self, widget):
        self.widget = widget
        self.material = None
        self.widget.addItem('Color 0')
        self.widget.addItem('Alpha 0')
        self.widget.addItem('Color 1')
        self.widget.addItem('Alpha 1')

    def currentLightingModePath(self):
        row = self.widget.currentRow()
        assert row != -1
        if row % 2 == 0:
            return +_p.channels[row//2].color_mode
        else:
            return +_p.channels[row//2].alpha_mode

    def currentLightingMode(self):
        return self.currentLightingModePath().get_value(self.material)

    def setMaterial(self, material):
        if self.material is not None:
            self.material.unregister_listener(self)
        self.material = material
        self.widget.setCurrentRow(-1)
        self.reload()
        self.material.register_listener(self)

    def clear(self):
        if self.material is not None:
            self.material.unregister_listener(self)
        self.material = None
        self.widget.setCurrentRow(-1)

    def reload(self):
        if self.widget.currentRow() == -1 and self.material.channel_count > 0:
            self.widget.setCurrentRow(0)
        elif self.widget.currentRow() >= 2*self.material.channel_count:
            self.widget.setCurrentRow(2*self.material.channel_count - 1)

        for i in range(self.material.channel_count):
            color_item = self.widget.item(2*i)
            alpha_item = self.widget.item(2*i + 1)
            color_item.setFlags(color_item.flags() | QtCore.Qt.ItemIsEnabled)
            alpha_item.setFlags(alpha_item.flags() | QtCore.Qt.ItemIsEnabled)
        for i in range(self.material.channel_count, 2):
            color_item = self.widget.item(2*i)
            alpha_item = self.widget.item(2*i + 1)
            color_item.setFlags(color_item.flags() & ~QtCore.Qt.ItemIsEnabled)
            alpha_item.setFlags(alpha_item.flags() & ~QtCore.Qt.ItemIsEnabled)

    def handle_event(self, event, path):
        if isinstance(event, views.ValueChangedEvent):
            if path == +_p.channel_count:
                self.reload()


class ChannelDialog(QtWidgets.QDialog):

    commitViewValue = QtCore.pyqtSignal(views.Path, object, object, str)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.ui = uic.loadUi(io.BytesIO(pkgutil.get_data(__package__, 'ChannelDialog.ui')), self)

        self.material = None

        for i in range(3):
            self.channel_count.addItem(str(i), i)
        for value in gx.ChannelSource:
            self.material_source.addItem(value.name, value)
            self.ambient_source.addItem(value.name, value)
        for value in gx.DiffuseFunction:
            self.diffuse_function.addItem(value.name, value)
        for value in gx.AttenuationFunction:
            self.attenuation_function.addItem(value.name, value)

        self.channel_count_handler = ViewHandler()
        self.channel_count_handler.add_widget(+_p.channel_count, ComboBoxAdaptor(self.channel_count), 'Num. Channels')
        self.channel_count_handler.commitViewValue.connect(self.commitViewValue)

        self.lighting_mode_list_handler = LightingModeListHandler(self.lighting_mode_list)

        self.lighting_mode_handler = ViewHandler()
        self.lighting_mode_handler.add_widget(+_p.material_source, ComboBoxAdaptor(self.material_source), 'Mat. Source')
        self.lighting_mode_handler.add_widget(+_p.ambient_source, ComboBoxAdaptor(self.ambient_source), 'Amb. Source')
        self.lighting_mode_handler.add_widget(+_p.diffuse_function, ComboBoxAdaptor(self.diffuse_function), 'Diff. Function')
        self.lighting_mode_handler.add_widget(+_p.attenuation_function, ComboBoxAdaptor(self.attenuation_function), 'Attn. Function')
        self.lighting_mode_handler.add_widget(+_p.light_enable, CheckBoxAdaptor(self.light_enable), 'Light Enable')
        light_mask = LightMaskAdaptor([
            self.use_light0, self.use_light1, self.use_light2, self.use_light3,
            self.use_light4, self.use_light5, self.use_light6, self.use_light7
        ])
        self.lighting_mode_handler.add_widget(+_p.light_mask, light_mask, 'Light Mask')
        self.lighting_mode_handler.commitViewValue.connect(self.on_lighting_mode_handler_commitViewValue)

        self.setEnabled(False)

    def setMaterial(self, material):
        self.material = material
        self.channel_count_handler.setView(material)
        self.lighting_mode_list_handler.setMaterial(material)
        self.setEnabled(True)

    def clear(self):
        self.channel_count_handler.clear()
        self.lighting_mode_list_handler.clear()
        self.setEnabled(False)

    @QtCore.pyqtSlot(views.Path, object, object, str)
    def on_lighting_mode_handler_commitViewValue(self, path, old_value, new_value, label):
        lighting_mode_path = self.lighting_mode_list_handler.currentLightingModePath()
        self.commitViewValue.emit(lighting_mode_path + path, old_value, new_value, label)

    @QtCore.pyqtSlot(int)
    def on_lighting_mode_list_currentRowChanged(self, row):
        if row == -1:
            self.lighting_mode_handler.clear()
            self.lighting_mode_handler.setEnabled(False)
            return
        self.lighting_mode_handler.setView(self.lighting_mode_list_handler.currentLightingMode())
        self.lighting_mode_handler.setEnabled(True)

