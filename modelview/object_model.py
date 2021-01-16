import weakref
#TODO remove gl dependency
import gl
from modelview.path import Path


class ValueChangedEvent:
    pass


class ItemInsertEvent:

    def __init__(self, index):
        self.index = index


class ItemRemoveEvent:

    def __init__(self, index):
        self.index = index


class ListenerRegistration:

    def __init__(self, listener, path):
        # A listener will usually hold a reference to the model, so to avoid
        # reference cycles, we take a weak reference to the listener
        self.listener_reference = weakref.ref(listener)
        self.path = path

    @property
    def listener(self):
        return self.listener_reference()

    @property
    def still_active(self):
        return self.listener_reference() is not None


class ObjectModel(gl.ResourceManagerMixin):

    def __init__(self):
        super().__init__()
        self._listener_registrations = []

    def register_listener(self, listener, path=Path()):
        registration = ListenerRegistration(listener, path)
        self._listener_registrations.append(registration)

    def unregister_listener(self, listener):
        i = 0
        while i < len(self._listener_registrations):
            registration = self._listener_registrations[i]
            if not registration.still_active:
                del self._listener_registrations[i]
                continue
            if registration.listener is listener:
                del self._listener_registrations[i]
                return
            i += 1
        assert False

    def emit_event(self, event, path=Path()):
        i = 0
        while i < len(self._listener_registrations):
            registration = self._listener_registrations[i]
            if not registration.still_active:
                del self._listener_registrations[i]
                continue
            registration.listener.handle_event(event, registration.path + path)
            i += 1

    def handle_event(self, event, path=Path()):
        self.emit_event(event, path)

    def _attach_child(self, child, path):
        self.gl_manage_resource(child)
        child.register_listener(self, path)

    def _detach_child(self, child):
        self.gl_delete_resource(child)
        child.unregister_listener(self)


class ReferenceAttribute:

    def __init__(self):
        self.path = None
        self.private_name = None

    def __set_name__(self, owner, name):
        self.path = Path.for_attribute(name)
        self.private_name = '_' + name

    def __get__(self, instance, owner=None):
        return getattr(instance, self.private_name)

    def __set__(self, instance, value):
        try:
            current_value = getattr(instance, self.private_name)
        except AttributeError:
            pass
        else:
            if value == current_value:
                return
            if current_value is not None:
                current_value.unregister_listener(instance)
        setattr(instance, self.private_name, value)
        if value is not None:
            value.register_listener(instance, self.path)
        instance.handle_event(ValueChangedEvent(), self.path)


class ReferenceList(ObjectModel):

    def __init__(self, items=tuple()):
        super().__init__()
        self._items = list(items)
        for i, item in enumerate(self._items):
            if item is not None:
                item.register_listener(self, Path.for_item(i))

    def __getitem__(self, index):
        return self._items[index]

    def __setitem__(self, index, item):
        current_item = self._items[index]
        if item == current_item:
            return
        if current_item is not None:
            current_item.unregister_listener(self)
        self._items[index] = item
        if item is not None:
            item.register_listener(self, Path.for_item(index))
        self.handle_event(ValueChangedEvent(), Path.for_item(index))

