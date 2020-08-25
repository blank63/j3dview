import weakref


class AttributeChangedEvent:
    #TODO pass attribute name
    pass


class View:

    def __init__(self, viewed_object):
        self.viewed_object = viewed_object
        self._listeners = []

    def register_listener(self, listener):
        self._listeners.append(weakref.ref(listener))

    def unregister_listener(self, listener):
        i = 0
        while i < len(self._listeners):
            current = self._listeners[i]()
            if current is None:
                del self._listeners[i]
                continue
            if current is listener:
                del self._listeners[i]
                break
            i += 1

    def send_event(self, event):
        i = 0
        while i < len(self._listeners):
            listener = self._listeners[i]()
            if listener is None:
                del self._listeners[i]
                continue
            listener.receive_event(self, event)
            i += 1


class SubView:

    def __init__(self, parent, attribute_name):
        self._parent = weakref.ref(parent)
        self._attribute_name = attribute_name

    @property
    def viewed_object(self):
        return getattr(self._parent().viewed_object, self._attribute_name)

    def send_event(self, event):
        self._parent().send_event(event)


class ReadOnlyAttribute:

    def __set_name__(self, owner, name):
        self.attribute_name = name

    def __get__(self, instance, owner=None):
        return getattr(instance.viewed_object, self.attribute_name)


class Attribute:

    def __set_name__(self, owner, name):
        self.attribute_name = name
        self.private_name = '_' + name

    def attribute_changed(self, instance):
        instance.send_event(AttributeChangedEvent())

    def __get__(self, instance, owner=None):
        try:
            return getattr(instance, self.private_name)
        except AttributeError:
            pass
        return getattr(instance.viewed_object, self.attribute_name)

    def __set__(self, instance, value):
        try:
            current_value = self.__get__(instance)
            if value == current_value:
                return
        except AttributeError:
            pass
        setattr(instance, self.private_name, value)
        self.attribute_changed(instance)


class SubViewAttribute:

    def __init__(self, sub_view_type):
        self.sub_view_type = sub_view_type

    def __set_name__(self, owner, name):
        self.attribute_name = name
        self.private_name = '_' + name

    def __get__(self, instance, owner=None):
        try:
            return getattr(instance, self.private_name)
        except AttributeError:
            pass
        sub_view = self.sub_view_type(instance, self.attribute_name)
        setattr(instance, self.private_name, sub_view)
        return sub_view

