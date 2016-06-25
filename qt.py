from PyQt5 import QtCore,QtWidgets


class ComboBox(QtWidgets.QComboBox):

    def setItems(self,items):
        self.items = items
        self.clear()
        self.addItems([item.name for item in items])
        for i,item in enumerate(items):
            self.setItemData(i,item)

    def setValue(self,value):
        self.setCurrentIndex(self.items.index(value))


class PropertyUndoCommand(QtWidgets.QUndoCommand):

    def __init__(self,property_owner,property_name,old_value,new_value):
        super().__init__()
        self.property_owner = property_owner
        self.property_name = property_name
        self.old_value = old_value
        self.new_value = new_value
        #FIXME: Set the text property to something? 

    def redo(self):
        setattr(self.property_owner,self.property_name,self.new_value)

    def undo(self):
        setattr(self.property_owner,self.property_name,self.old_value)


class PropertyWidget:

    def __init__(self):
        self.property_owner = None
        self.property_name = None
        self.property_changed_signal = None
        self.undo_stack = None

    def bindProperty(self,property_owner,property_name,property_changed_signal):
        if self.property_changed_signal is not None:
            self.property_changed_signal.disconnect(self.setValue)

        self.property_owner = property_owner
        self.property_name = property_name
        self.setValue(getattr(self.property_owner,self.property_name))

        self.property_changed_signal = property_changed_signal
        self.property_changed_signal.connect(self.setValue)

    def setUndoStack(self,undo_stack):
        self.undo_stack = undo_stack

    def updatePropertyValue(self,value):
        if self.property_owner is None: return
        old_value = getattr(self.property_owner,self.property_name)
        if value == old_value: return
        if self.undo_stack is not None:
            self.undo_stack.push(PropertyUndoCommand(self.property_owner,self.property_name,old_value,value))
        else:
            setattr(self.property_owner,self.property_name,value)


class PropertyLineEdit(QtWidgets.QLineEdit,PropertyWidget):

    def __init__(self,*args,**kwargs):
        QtWidgets.QLineEdit.__init__(self,*args,**kwargs)
        PropertyWidget.__init__(self)
        self.editingFinished.connect(self.on_editingFinished)

    @QtCore.pyqtSlot(str)
    def setValue(self,value):
        self.setText(value)

    @QtCore.pyqtSlot()
    def on_editingFinished(self):
        self.updatePropertyValue(self.text())


class PropertyComboBox(ComboBox,PropertyWidget):

    def __init__(self,*args,**kwargs):
        ComboBox.__init__(self,*args,**kwargs)
        PropertyWidget.__init__(self)
        self.currentIndexChanged.connect(self.on_currentIndexChanged)

    @QtCore.pyqtSlot(int)
    def on_currentIndexChanged(self,index):
        self.updatePropertyValue(self.itemData(index))


class PropertySpinBox(QtWidgets.QSpinBox,PropertyWidget):

    def __init__(self,*args,**kwargs):
        QtWidgets.QSpinBox.__init__(self,*args,**kwargs)
        PropertyWidget.__init__(self)
        self.setKeyboardTracking(False)
        self.valueChanged.connect(self.updatePropertyValue)


class PropertyDoubleSpinBox(QtWidgets.QDoubleSpinBox,PropertyWidget):

    def __init__(self,*args,**kwargs):
        QtWidgets.QSpinBox.__init__(self,*args,**kwargs)
        PropertyWidget.__init__(self)
        self.setKeyboardTracking(False)
        self.valueChanged.connect(self.updatePropertyValue)


class Property:

    def __init__(self,property_type=object):
        self.property_type = property_type

    @staticmethod
    def create_getter(property_name):
        def getter(property_owner):
            return getattr(property_owner,'_' + property_name)
        return getter

    @staticmethod
    def create_setter(property_name):
        def setter(property_owner,value):
            setattr(property_owner,'_' + property_name,value)
        return setter

    def create_full_setter(self,property_name,notify_name):
        internal_setter = self.create_setter(property_name)

        def setter(property_owner,value):
            try:
                old_value = getattr(property_owner,property_name)
            except AttributeError:
                pass
            else:
                if value == old_value: return

            internal_setter(property_owner,value)

            getattr(property_owner,notify_name).emit(value)

        return setter


class PropertyOwnerMetaClass(QtCore.pyqtWrapperType):

    def __new__(metacls,cls,bases,classdict):
        property_items = [(key,value) for key,value in classdict.items() if isinstance(value,Property)]

        for name,property_placeholder in property_items:
            metacls.insert_property(classdict,name,property_placeholder)

        return super().__new__(metacls,cls,bases,classdict)

    @staticmethod
    def insert_property(classdict,name,property_placeholder):
        notify_name = name + '_changed'
        notify = QtCore.pyqtSignal(property_placeholder.property_type)
        classdict[notify_name] = notify

        getter = property_placeholder.create_getter(name)
        setter = property_placeholder.create_full_setter(name,notify_name)
        classdict[name] = property(getter,setter)


class Wrapper(QtCore.QObject,metaclass=PropertyOwnerMetaClass):

    class Property(Property):

        @staticmethod
        def create_getter(property_name):
            def getter(property_owner):
                return getattr(property_owner.wrapped_object,property_name)
            return getter

        @staticmethod
        def create_setter(property_name):
            def setter(property_owner,value):
                setattr(property_owner.wrapped_object,property_name,value)
            return setter

    def __init__(self,wrapped_object,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.wrapped_object = wrapped_object

    def __getattr__(self,name):
        return getattr(self.wrapped_object,name)

