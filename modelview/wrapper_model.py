from modelview.path import Path
from modelview.object_model import (
    ObjectModel,
    ValueChangedEvent,
    ItemInsertEvent,
    ItemRemoveEvent
)


class WrapperModel(ObjectModel):

    def __init__(self, wrapped_object):
        super().__init__()
        self.wrapped_object = wrapped_object


class Attribute:

    def __init__(self, source_path=None):
        self.path = None
        self.source_path = source_path

    def __set_name__(self, owner, name):
        self.path = Path.for_attribute(name)
        if self.source_path is None:
            self.source_path = self.path

    def attribute_changed(self, instance):
        instance.handle_event(ValueChangedEvent(), self.path)

    def __get__(self, instance, owner=None):
        return self.source_path.get_value(instance.wrapped_object)

    def __set__(self, instance, value):
        current_value = self.__get__(instance)
        if value == current_value:
            return
        self.source_path.set_value(instance.wrapped_object, value)
        self.attribute_changed(instance)


class WrapperAttribute:

    def __init__(self, attribute_type, source_path=None):
        self.attribute_type = attribute_type
        self.path = None
        self.source_path = source_path
        self.private_name = None

    def __set_name__(self, owner, name):
        self.path = Path.for_attribute(name)
        if self.source_path is None:
            self.source_path = self.path
        self.private_name = '_' + name

    def __get__(self, instance, owner=None):
        try:
            return getattr(instance, self.private_name)
        except AttributeError:
            pass
        wrapped_object = self.source_path.get_value(instance.wrapped_object)
        wrapper = self.attribute_type(wrapped_object)
        instance._attach_child(wrapper, self.path)
        setattr(instance, self.private_name, wrapper)
        return wrapper


def wrapper_attribute(attribute_type=None, source_path=None):
    if attribute_type is None:
        return Attribute(source_path=source_path)
    return WrapperAttribute(attribute_type, source_path=source_path)


class List(WrapperModel):

    def __len__(self):
        return len(self.wrapped_object)

    def __getitem__(self, key):
        return self.wrapped_object[key]

    def __setitem__(self, key, value):
        current_value = self.wrapped_object[key]
        if value == current_value:
            return
        self.wrapped_object[key] = value
        self.handle_event(ValueChangedEvent(), Path.for_item(key))


class WrapperList(WrapperModel):

    def __init__(self, item_type, wrapped_object):
        super().__init__(wrapped_object)
        self._items = [item_type(item) for item in wrapped_object]
        for i, item in enumerate(self._items):
            self._attach_child(item, Path.for_item(i))

    def __len__(self):
        return len(self._items)

    def __getitem__(self, key):
        return self._items[key]

    def __delitem__(self, key):
        assert isinstance(key, int)
        assert key >= 0
        self._detach_child(self._items[key])
        del self._items[key]
        del self.wrapped_object[key]
        for i in range(key, len(self)):
            item = self._items[i]
            item.unregister_listener(self)
            item.register_listener(self, Path.for_item(i))
        self.handle_event(ItemRemoveEvent(key))

    def insert(self, index, item):
        assert index >= 0
        self.wrapped_object.insert(index, item.wrapped_object)
        self._items.insert(index, item)
        self._attach_child(item, Path.for_item(index))
        for i in range(index + 1, len(self)):
            item = self._items[i]
            item.unregister_listener(self)
            item.register_listener(self, Path.for_item(i))
        self.handle_event(ItemInsertEvent(index))

    def index(self, value):
        return self._items.index(value)


def wrapper_list(item_type=None):
    if item_type is None:
        return List
    return lambda wrapped_object: WrapperList(item_type, wrapped_object)

