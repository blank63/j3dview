from PyQt5 import QtWidgets
import gl


class ComboBox(QtWidgets.QComboBox):

    def setCurrentData(self, value):
        index = self.findData(value)
        assert index != -1
        self.setCurrentIndex(index)

    def addEnumItems(self, enum_type):
        for value in enum_type:
            self.addItem(value.name, value)

