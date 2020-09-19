import weakref


class PathFragment:

    def __add__(self, other):
        if isinstance(other, PathFragment):
            return Path((self, other))
        if isinstance(other, Path):
            return Path((self, *other))
        return NotImplemented


class AttributePathFragment(PathFragment):

    def __init__(self, attribute_name):
        self.attribute_name = attribute_name

    def match(self, other):
        if not isinstance(other, AttributePathFragment):
            return False
        return self.attribute_name == other.attribute_name


class ItemPathFragment(PathFragment):

    def __init__(self, key):
        self.key = key

    def match(self, other):
        if not isinstance(other, ItemPathFragment):
            return False
        if self.key is ... or other.key is ...:
            return True
        return self.key == other.key


class Path(tuple):

    def __add__(self, other):
        if isinstance(other, PathFragment):
            return Path((*self, other))
        if isinstance(other, Path):
            return Path((*self, *other))
        return NotImplemented

    def match(self, other):
        return all(a.match(b) for a, b in zip(self, other))


class PathBuilder:

    def __init__(self, path=Path()):
        self.__path = path

    def __getattr__(self, attribute_name):
        return PathBuilder(self.__path + AttributePathFragment(attribute_name))

    def __getitem__(self, key):
        return PathBuilder(self.__path + ItemPathFragment(key))

    def __pos__(self):
        """Return the built path.

        Using the unary plus operator for this is admittedly somewhat jank, but
        it allows for path building to be expressed very succinctly."""
        return self.__path


path_builder = PathBuilder()


class ValueChangedEvent:
    pass


class ListenerRegistration:

    def __init__(self, listener, path):
        # A listener will usually hold a reference to the view, so to avoid
        # reference cycles, we take a weak reference to the listener
        self.listener_reference = weakref.ref(listener)
        self.path = path

    @property
    def listener(self):
        return self.listener_reference()

    @property
    def still_active(self):
        return self.listener_reference() is not None


class View:

    def __init__(self, viewed_object):
        self.viewed_object = viewed_object
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

    def send_event(self, event, path=Path()):
        i = 0
        while i < len(self._listener_registrations):
            registration = self._listener_registrations[i]
            if not registration.still_active:
                del self._listener_registrations[i]
                continue
            registration.listener.receive_event(event, registration.path + path)
            i += 1


class SubView:

    def __init__(self, parent, attribute_name):
        self._parent = weakref.ref(parent)
        self._attribute_name = attribute_name

    @property
    def viewed_object(self):
        return getattr(self._parent().viewed_object, self._attribute_name)

    def send_event(self, event, path):
        self._parent().send_event(event, AttributePathFragment(self._attribute_name) + path)


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
        instance.send_event(ValueChangedEvent(), AttributePathFragment(self.attribute_name))

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

