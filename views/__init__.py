import weakref
import gl


class AttributePathFragment:

    __slots__ = ['name']

    def __init__(self, name):
        super().__setattr__('name', name)

    def __setattr__(self, name, value):
        raise AttributeError(f'Cannot assign to field {name}')

    def __delattr__(self, name):
        raise AttributeError(f'Cannot delete field {name}')

    def __eq__(self, other):
        if not isinstance(other, AttributePathFragment):
            return False
        return self.name == other.name

    def __hash__(self):
        return hash(self.name)

    def __str__(self):
        return f'.{self.name}'

    def match(self, other):
        return self == other

    def get_value(self, obj):
        return getattr(obj, self.name)

    def set_value(self, obj, value):
        setattr(obj, self.name, value)


class ItemPathFragment:

    __slots__ = ['key']

    def __init__(self, key):
        super().__setattr__('key', key)

    def __setattr__(self, name, value):
        raise AttributeError(f'Cannot assign to field {name}')

    def __delattr__(self, name):
        raise AttributeError(f'Cannot delete field {name}')

    def __eq__(self, other):
        if not isinstance(other, ItemPathFragment):
            return False
        return self.key == other.key

    def __hash__(self):
        return hash(self.key)

    def __str__(self):
        return f'[{self.key}]'

    def match(self, other):
        if not isinstance(other, ItemPathFragment):
            return False
        if self.key is ... or other.key is ...:
            return True
        return self.key == other.key

    def get_value(self, obj):
        return obj[self.key]

    def set_value(self, obj, value):
        obj[self.key] = value


class Path(tuple):

    def __add__(self, other):
        if not isinstance(other, Path):
            return NotImplemented
        return Path((*self, *other))

    def __str__(self):
        return ''.join(str(fragment) for fragment in self)

    def match(self, other):
        if len(self) != len(other):
            return False
        return all(a.match(b) for a, b in zip(self, other))

    def get_value(self, obj):
        for fragment in self:
            obj = fragment.get_value(obj)
        return obj

    def set_value(self, obj, value):
        for i in range(len(self) - 1):
            obj = self[i].get_value(obj)
        self[-1].set_value(obj, value)

    @staticmethod
    def for_attribute(name):
        return Path((AttributePathFragment(name),))

    @staticmethod
    def for_item(key):
        return Path((ItemPathFragment(key),))


class PathBuilder:

    def __init__(self, path=Path()):
        self.__path = path

    def __getattr__(self, name):
        return PathBuilder(self.__path + Path.for_attribute(name))

    def __getitem__(self, key):
        return PathBuilder(self.__path + Path.for_item(key))

    def __pos__(self):
        """Return the built path.

        Using the unary plus operator for this is admittedly somewhat jank, but
        it allows for path building to be expressed very succinctly.
        """
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


class View(gl.ResourceManagerMixin):

    def __init__(self, viewed_object):
        super().__init__()
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

    def _create_child_view(self, path, view_type, viewed_object, *args, **kwargs):
        view = self.gl_create_resource(view_type, viewed_object, *args, **kwargs)
        view.register_listener(self, path)
        return view

    def _delete_child_view(self, view):
        self.gl_delete_resource(view)
        view.unregister_listener(self)


class ListView(View):

    def __len__(self):
        return len(self.viewed_object)

    def __getitem__(self, key):
        return self.viewed_object[key]

    def __setitem__(self, key, value):
        if value == self.viewed_object[key]:
            return
        self.viewed_object[key] = value
        self.handle_event(ValueChangedEvent(), Path.for_item(key))


class ViewListView(View):

    def __init__(self, viewed_object, item_type):
        super().__init__(viewed_object)
        self._item_type = item_type
        self._items = [
            self._create_child_view(Path.for_item(i), item_type, item)
            for i, item in enumerate(viewed_object)
        ]

    def __len__(self):
        return len(self._items)

    def __getitem__(self, key):
        return self._items[key]

    def __setitem__(self, key, value):
        if value == self._items[key].viewed_object:
            return
        self._delete_child_view(self._items[key])
        path = Path.for_item(key)
        self.viewed_object[key] = value
        self._items[key] = self._create_child_view(path, self._item_type, value)
        self.handle_event(ValueChangedEvent(), path)

    def index(self, value):
        return self._items.index(value)


class ReadOnlyAttribute:

    def __set_name__(self, owner, name):
        self.name = name

    def __get__(self, instance, owner=None):
        return getattr(instance.viewed_object, self.name)


class Attribute:

    def __set_name__(self, owner, name):
        self.name = name
        self.path = Path.for_attribute(name)

    def attribute_changed(self, instance):
        instance.handle_event(ValueChangedEvent(), self.path)

    def __get__(self, instance, owner=None):
        return getattr(instance.viewed_object, self.name)

    def __set__(self, instance, value):
        current_value = self.__get__(instance)
        if value == current_value:
            return
        setattr(instance.viewed_object, self.name, value)
        self.attribute_changed(instance)


class ViewAttribute:

    def __init__(self, view_type, *view_args, **view_kwargs):
        self.view_type = view_type
        self.view_args = view_args
        self.view_kwargs = view_kwargs

    def __set_name__(self, owner, name):
        self.name = name
        self.path = Path.for_attribute(name)
        self.private_name = '_' + name

    def __get__(self, instance, owner=None):
        try:
            return getattr(instance, self.private_name)
        except AttributeError:
            pass
        viewed_object = getattr(instance.viewed_object, self.name)
        view = instance._create_child_view(
            self.path, self.view_type, viewed_object,
            *self.view_args, **self.view_kwargs
        )
        setattr(instance, self.private_name, view)
        return view

