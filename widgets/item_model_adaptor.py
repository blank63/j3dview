import weakref
from PyQt5.QtCore import Qt
from PyQt5 import QtCore
from modelview.object_model import ItemInsertEvent, ItemRemoveEvent
from widgets.modelview import UndoCommand, AbstractItemModel


class SetObjectModelDataCommand(UndoCommand):

    def __init__(self, object_model, path, value):
        super().__init__()
        self.object_model = object_model 
        self.path = path
        self.old_value = path.get_value(object_model)
        self.new_value = value
        if self.new_value == self.old_value:
            self.setObsolete(True)

    def mergeWith(self, other):
        if not isinstance(other, SetObjectModelDataCommand):
            return False
        if self.object_model is not other.object_model:
            return False
        if self.path != other.path:
            return False
        assert self.new_value == other.old_value
        self.new_value = other.new_value
        if self.new_value == self.old_value:
            self.setObsolete(True)
        return True

    def redo(self):
        self.path.set_value(self.object_model, self.new_value)

    def undo(self):
        self.path.set_value(self.object_model, self.old_value)


class AbstractEntry:

    def __init__(self):
        self.item_reference = None
        self.model_reference = None

    @property
    def item(self):
        if self.item_reference is None:
            return None
        return self.item_reference()

    @property
    def model(self):
        if self.model_reference is None:
            return None
        return self.model_reference()

    def set_item(self, item):
        self.item_reference = weakref.ref(item)

    def attach_model(self, model):
        self.model_reference = weakref.ref(model)

    def detach_model(self):
        self.model_reference = None

    def get_flags(self):
        return Qt.NoItemFlags

    def get_data(self, role):
        return None

    def set_data(self, value, role):
        return False

    def handle_event(self, event, path):
        pass


class Entry(AbstractEntry):

    def __init__(self, *, data=None, role_data=None, path=None, role_paths=None,
            label='property', enabled=True, selectable=True, editable=False,
            drag_enabled=False, drop_enabled=False):
        if role_data is not None:
            self.role_data = dict(role_data)
        else:
            self.role_data = {}
        self.role_data.setdefault(Qt.DisplayRole, data)

        if role_paths is not None:
            self.role_paths = dict(role_paths)
        else:
            self.role_paths = {}
        if path is not None:
            self.role_paths.setdefault(Qt.DisplayRole, path)
            self.role_paths.setdefault(Qt.EditRole, path)

        self.label = label

        self.flags = Qt.NoItemFlags
        if enabled:
            self.flags |= Qt.ItemIsEnabled
        if selectable:
            self.flags |= Qt.ItemIsSelectable
        if editable:
            self.flags |= Qt.ItemIsEditable
        if drag_enabled:
            self.flags |= Qt.ItemIsDragEnabled
        if drop_enabled:
            self.flags |= Qt.ItemIsDropEnabled

    def attach_model(self, model):
        super().attach_model(model)
        for trigger in self.role_paths.values():
            model.register_trigger(self, trigger)

    def detach_model(self):
        for trigger in self.role_paths.values():
            self.model.unregister_trigger(self, trigger)
        super().detach_model()

    def get_flags(self):
        return self.flags

    def get_data(self, role):
        path = self.role_paths.get(role)
        if path is not None:
            if not self.model.isValid():
                return None
            return self.model.get_object_data(path)
        if role == Qt.EditRole:
            role = Qt.DisplayRole
        return self.role_data.get(role)

    def set_data(self, value, role):
        path = self.role_paths.get(role)
        if path is not None:
            message = f"Changed '{self.label}'"
            self.model.commit_object_data(path, value, message)
            return True
        if role == Qt.EditRole:
            role = Qt.DisplayRole
        self.role_data[role] = value
        return True

    def handle_event(self, event, path):
        self.model.item_data_changed(self.item)


class AbstractItem:

    def __init__(self):
        self.parent_reference = None
        self.model_reference = None

    @property
    def parent(self):
        if self.parent_reference is None:
            return None
        return self.parent_reference()

    @property
    def model(self):
        if self.model_reference is None:
            return None
        return self.model_reference()

    def set_parent(self, parent):
        self.parent_reference = weakref.ref(parent)

    def attach_model(self, model):
        self.model_reference = weakref.ref(model)
        for i in range(self.child_count):
            self.get_child(i).attach_model(model)

    def detach_model(self):
        for i in range(self.child_count):
            self.get_child(i).detach_model()
        self.model_reference = None

    def reset(self):
        for i in range(self.child_count):
            self.get_child(i).reset()

    @property
    def column_count(self):
        return 0

    def get_flags(self, column):
        return Qt.NoItemFlags

    def get_data(self, column, role):
        return None

    def set_data(self, column, value, role):
        return False

    @property
    def child_count(self):
        return 0

    def get_child(self, row):
        pass

    def get_child_index(self, child):
        pass

    def handle_event(self, event, path):
        pass


class Item(AbstractItem):

    def __init__(self, entries=tuple(), *, column_count=None):
        super().__init__()
        if entries:
            assert column_count is None
            self.entries = list(entries)
        else:
            assert column_count is not None
            self.entries = [Entry() for _ in range(column_count)]
        for entry in self.entries:
            entry.set_item(self)
        self.children = []

    def attach_model(self, model):
        super().attach_model(model)
        for entry in self.entries:
            entry.attach_model(model)

    def detach_model(self):
        for entry in self.entries:
            entry.detach_model()
        super().detach_model()

    @property
    def column_count(self):
        return len(self.entries)

    def get_flags(self, column):
        return self.entries[column].get_flags()

    def get_data(self, column, role):
        return self.entries[column].get_data(role)

    def set_data(self, column, value, role):
        return self.entries[column].set_data(value, role)

    @property
    def child_count(self):
        return len(self.children)

    def insert_child(self, index, child):
        child.set_parent(self)
        self.children.insert(index, child)
        if self.model is not None:
            child.attach_model(self.model)

    def add_child(self, child):
        self.insert_child(self.child_count, child)

    def take_child(self, row):
        child = self.children[row]
        del self.children[row]
        child.detach_model()
        return child

    def get_child(self, row):
        return self.children[row]

    def get_child_index(self, child):
        return self.children.index(child)


class AbstractListItem(Item):

    def attach_model(self, model):
        super().attach_model(model)
        model.register_trigger(self, self.list_path)

    def detach_model(self):
        self.model.unregister_trigger(self, self.list_path)
        super().detach_model()

    def create_child(self, index):
        pass

    def reset(self):
        while self.child_count > 0:
            self.take_child(self.child_count - 1)
        if self.model.isValid():
            list_ = self.model.get_object_data(self.list_path)
            for i in range(len(list_)):
                item = self.create_child(i)
                self.add_child(item)
        super().reset()

    def handle_event(self, event, path):
        # Inserts/removes of child items always happens at the end of the child
        # list, no matter where the item was inserted/removed in the object that
        # originated the event. This assumes that all of the child items are
        # interchangeable, except for their index, and will not work if the
        # child items behaves differently from each other.
        if isinstance(event, ItemInsertEvent):
            row = event.index
            index = self.model.get_item_index(self)
            self.model.beginInsertRows(index, row, row)
            list_ = self.model.get_object_data(self.list_path)
            element_index = len(list_) - 1
            element = self.create_child(element_index)
            self.add_child(element)
            self.model.endInsertRows()
        elif isinstance(event, ItemRemoveEvent):
            row = event.index
            index = self.model.get_item_index(self)
            # At this point, the item has already been removed from the
            # originating object. But beginRemoveRows assumes that rows has not
            # yet been removed, and might therefore cause attempts to access the
            # removed item. As a workaround, before calling beginRemoveRows, we
            # remove the child item and instead insert a dummy child item that
            # doesn't reference anything. We then remove the dummy item between
            # calling beginRemoveRows and endRemoveRows.
            # There might be persistent model indices referencing the removed
            # child, so we keep a reference to it to prevent it from being
            # garbage collected until after endRemoveRows has been called.
            removed_child = self.take_child(self.child_count - 1)
            dummy = Item(column_count=0)
            self.insert_child(row, dummy)
            self.model.beginRemoveRows(index, row, row)
            self.take_child(row)
            self.model.endRemoveRows()


class ItemModelAdaptor(AbstractItemModel):

    def __init__(self, *, column_count=None, root_item=None):
        super().__init__()
        self.object_model = None
        self.trigger_table = {}
        if root_item is not None:
            assert column_count is None
            self.root_item = root_item
        else:
            assert column_count is not None
            self.root_item = Item(column_count=column_count)
        self.root_item.attach_model(self)

    def setObjectModel(self, object_model):
        if object_model is self.object_model:
            return
        self.beginResetModel()
        if self.object_model is not None:
            self.object_model.unregister_listener(self)
        self.object_model = object_model
        if self.object_model is not None:
            self.object_model.register_listener(self)
        self.root_item.reset()
        self.endResetModel()

    def isValid(self):
        return self.object_model is not None

    def register_trigger(self, item, path):
        self.trigger_table.setdefault(path, []).append(item)

    def unregister_trigger(self, item, path):
        self.trigger_table[path].remove(item)

    def get_item_index(self, item):
        if item is self.root_item:
            return QtCore.QModelIndex()
        row = item.parent.get_child_index(item)
        return self.createIndex(row, 0, item)

    def item_data_changed(self, item):
        left = self.get_item_index(item)
        right = self.sibling(left.row(), self.columnCount(left) - 1, left)
        self.dataChanged.emit(left, right)

    def get_object_data(self, path):
        return path.get_value(self.object_model)

    def commit_object_data(self, path, value, message):
        assert self.undo_stack is not None
        command = SetObjectModelDataCommand(self.object_model, path, value)
        command.setText(message)
        self.undo_stack.push(command)

    def add_top_level_item(self, item):
        self.root_item.add_child(item)

    def top_level_item_count(self):
        return self.root_item.child_count

    def index(self, row, column, parent=QtCore.QModelIndex()):
        if row < 0 or column < 0:
            return QtCore.QModelIndex()
        if parent.isValid():
            parent_item = parent.internalPointer()
        else:
            parent_item = self.root_item
        if row >= parent_item.child_count:
            return QtCore.QModelIndex()
        item = parent_item.get_child(row)
        if column >= item.column_count:
            return QtCore.QModelIndex()
        return self.createIndex(row, column, item)

    def parent(self, index):
        if not index.isValid():
            return QtCore.QModelIndex()
        item = index.internalPointer()
        parent_item = item.parent
        if parent_item is self.root_item:
            return QtCore.QModelIndex()
        row = parent_item.parent.get_child_index(parent_item)
        return self.createIndex(row, 0, parent_item)

    def rowCount(self, parent=QtCore.QModelIndex()):
        if parent.isValid():
            parent_item = parent.internalPointer()
        else:
            parent_item = self.root_item
        return parent_item.child_count

    def columnCount(self, parent=QtCore.QModelIndex()):
        if parent.isValid():
            parent_item = parent.internalPointer()
        else:
            parent_item = self.root_item
        return parent_item.column_count

    def flags(self, index):
        if not index.isValid():
            return Qt.NoItemFlags
        item = index.internalPointer()
        return item.get_flags(index.column())

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        item = index.internalPointer()
        return item.get_data(index.column(), role)

    def setData(self, index, value, role=Qt.EditRole):
        if not index.isValid():
            return False
        item = index.internalPointer()
        return item.set_data(index.column(), value, role)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if orientation != Qt.Horizontal:
            return None
        if section < 0 or section >= self.root_item.column_count:
            return None
        return self.root_item.get_data(section, role)

    def setHeaderData(self, section, orientation, value, role=Qt.EditRole):
        if orientation != Qt.Horizontal:
            return False
        if section < 0 or section >= self.root_item.column_count:
            return False
        return self.root_item.set_data(section, value, role)

    def handle_event(self, event, path):
        for item in self.trigger_table.get(path, []):
            item.handle_event(event, path)


