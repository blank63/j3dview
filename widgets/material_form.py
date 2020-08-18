import io
import pkgutil
from PyQt5 import QtWidgets, uic
import gx


class MaterialForm(QtWidgets.QWidget):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.ui = uic.loadUi(io.BytesIO(pkgutil.get_data(__package__, 'MaterialForm.ui')), self)

        self.cull_mode.addEnumItems(gx.CullMode)

        self.alpha_test_function0.addEnumItems(gx.CompareFunction)
        self.alpha_test_function1.addEnumItems(gx.CompareFunction)
        self.alpha_test_operator.addEnumItems(gx.AlphaOperator)

        self.depth_mode_function.addEnumItems(gx.CompareFunction)

        self.blend_mode_function.addEnumItems(gx.BlendFunction)
        self.blend_mode_source_factor.addEnumItems(gx.BlendSourceFactor)
        self.blend_mode_destination_factor.addEnumItems(gx.BlendDestinationFactor)
        self.blend_mode_logical_operation.addEnumItems(gx.LogicalOperation)

        self.setEnabled(False)

        self.material = None

    def setMaterial(self, material):
        self.material = material
        self.reload()
        self.setEnabled(True)

    def reload(self):
        self.name.setText(self.material.name)
        self.unknown0.setValue(self.material.unknown0)
        self.cull_mode.setCurrentData(self.material.cull_mode)
        self.dither.setChecked(self.material.dither)

        self.alpha_test_function0.setCurrentData(self.material.alpha_test.function0)
        self.alpha_test_reference0.setValue(self.material.alpha_test.reference0)
        self.alpha_test_function1.setCurrentData(self.material.alpha_test.function1)
        self.alpha_test_reference1.setValue(self.material.alpha_test.reference1)
        self.alpha_test_operator.setCurrentData(self.material.alpha_test.operator)

        self.depth_mode_enable.setChecked(self.material.depth_mode.enable)
        self.depth_mode_test_early.setChecked(self.material.depth_test_early)
        self.depth_mode_function.setCurrentData(self.material.depth_mode.function)
        self.depth_mode_update_enable.setChecked(self.material.depth_mode.update_enable)

        self.blend_mode_function.setCurrentData(self.material.blend_mode.function)
        self.blend_mode_source_factor.setCurrentData(self.material.blend_mode.source_factor)
        self.blend_mode_destination_factor.setCurrentData(self.material.blend_mode.destination_factor)
        self.blend_mode_logical_operation.setCurrentData(self.material.blend_mode.logical_operation)

