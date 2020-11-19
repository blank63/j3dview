import io
import pkgutil
import weakref
from PyQt5 import QtCore, QtGui, QtWidgets, uic
import gx
import views
from views import path_builder as _p


PathRole = QtCore.Qt.UserRole


class Item:

    def __init__(self):
        self.parent_reference = None
        self.children = []
        self.enabled = True

    @property
    def parent(self):
        return self.parent_reference()

    def set_parent(self, parent):
        self.parent_reference = weakref.ref(parent)

    def set_enabled(self, value):
        self.enabled = value
        for child in self.children:
            child.set_enabled(value)

    def add_child(self, child):
        child.set_parent(self)
        self.children.append(child)

    def get_child(self, row):
        return self.children[row]

    @property
    def child_count(self):
        return len(self.children)

    def get_child_index(self, child):
        return self.children.index(child)

    @property
    def column_count(self):
        return 0

    def get_flags(self, column):
        return QtCore.Qt.NoItemFlags

    def get_data(self, view, column, role):
        return QtCore.QVariant()

    def set_data(self, view, column, value, role):
        return False


class GroupItem(Item):

    def __init__(self, labels=[]):
        super().__init__()
        self.labels = labels

    def set_labels(self, labels):
        self.labels = labels

    @property
    def column_count(self):
        return len(self.labels)

    def get_flags(self, column):
        if not self.enabled:
            return QtCore.Qt.NoItemFlags
        return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

    def get_data(self, view, column, role):
        if role != QtCore.Qt.DisplayRole:
            return QtCore.QVariant()
        return self.labels[column]


class PropertyItem(Item):

    def __init__(self, label, path):
        super().__init__()
        self.label = label
        self.path = path

    @property
    def column_count(self):
        return 2

    def get_flags(self, column):
        if not self.enabled:
            return QtCore.Qt.NoItemFlags
        if column == 0:
            return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
        if column == 1:
            return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEditable
        assert False

    def get_data(self, view, column, role):
        if column == 0:
            if role == QtCore.Qt.DisplayRole:
                return self.label
            return QtCore.QVariant()
        if column == 1:
            if role in {QtCore.Qt.DisplayRole, QtCore.Qt.EditRole}:
                return self.path.get_value(view)
            if role == PathRole:
                return self.path
            return QtCore.QVariant()
        assert False

    def set_data(self, view, column, value, role):
        if column != 1:
            return False
        if role != QtCore.Qt.EditRole:
            return False
        self.path.set_value(view, value)
        return True


class ModelAdaptor(QtCore.QAbstractItemModel):

    def __init__(self, view):
        super().__init__()
        self.root_item = GroupItem()
        self.view = view

    def set_header_labels(self, labels):
        self.root_item.set_labels(labels)

    def add_item(self, item, parent_item=None):
        if parent_item is None:
            parent_item = self.root_item
        parent_item.add_child(item)

    def get_item_index(self, item):
        if item is self.root_item:
            return QtCore.QModelIndex()
        row = item.parent.get_child_index(item)
        return self.createIndex(row, 0, item)

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
            return QtCore.Qt.NoItemFlags
        item = index.internalPointer()
        return item.get_flags(index.column())

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if not index.isValid():
            return QtCore.QVariant()
        item = index.internalPointer()
        return item.get_data(self.view, index.column(), role)

    def setData(self, index, value, role=QtCore.Qt.EditRole):
        if not index.isValid():
            return False
        item = index.internalPointer()
        success = item.set_data(self.view, index.column(), value, role)
        if success:
            self.dataChanged.emit(index, index)
        return success

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if orientation != QtCore.Qt.Horizontal:
            return QtCore.QVariant()
        if section < 0 or section >= self.root_item.column_count:
            return QtCore.QVariant()
        return self.root_item.get_data(self.view, section, role)


class MaterialAdaptor(ModelAdaptor):

    def __init__(self, material):
        super().__init__(material)
        self.set_header_labels(['Property', 'Value'])
        material.register_listener(self)

        self.add_item(PropertyItem('Num. Channels', +_p.channel_count))
        self.channel_list = GroupItem(['Channels', ''])
        self.add_item(self.channel_list)
        for i in range(2):
            channel = GroupItem([f'Channel {i}', ''])
            self.add_item(channel, self.channel_list)
            self.add_lighting_mode('Color', +_p.channels[i].color_mode, channel)
            self.add_lighting_mode('Alpha', +_p.channels[i].alpha_mode, channel)

        self.add_item(PropertyItem('Num. Tex. Gens.', +_p.texcoord_generator_count))
        self.texcoord_generator_list = GroupItem(['Tex. Gens.', ''])
        self.add_item(self.texcoord_generator_list)
        for i in range(8):
            self.add_texcoord_generator(f'Tex. Gen. {i}', +_p.texcoord_generators[i], self.texcoord_generator_list)

        texture_matrix_list = GroupItem(['Texture Matrices', ''])
        self.add_item(texture_matrix_list)
        for i in range(10):
            self.add_texture_matrix(f'Texture Matrix {i}', +_p.texture_matrices[i], texture_matrix_list)

        self.add_item(PropertyItem('Num. TEV Stages', +_p.tev_stage_count))
        self.tev_stage_list = GroupItem(['TEV Stages', ''])
        self.add_item(self.tev_stage_list)
        for i in range(16):
            self.add_tev_stage(f'TEV Stage {i}', +_p.tev_stages[i], self.tev_stage_list)

        swap_table_list = GroupItem(['Swap Tables', ''])
        self.add_item(swap_table_list)
        for i in range(4):
            self.add_swap_table(f'Swap Table {i}', +_p.swap_tables[i], swap_table_list)

        self.add_item(PropertyItem('Num. Indirect Stages', +_p.indirect_stage_count))
        self.indirect_stage_list = GroupItem(['Indirect Stages', ''])
        self.add_item(self.indirect_stage_list)
        for i in range(4):
            self.add_indirect_stage(f'Indirect Stage {i}', +_p.indirect_stages[i], self.indirect_stage_list)

        self.update_channel_list()
        self.update_texcoord_generator_list()
        self.update_tev_stage_list()
        self.update_indirect_stage_list()

    def add_lighting_mode(self, label, path, parent):
        lighting_mode = GroupItem([label, ''])
        self.add_item(lighting_mode, parent)
        self.add_item(PropertyItem('Mat. Source', path + _p.material_source), lighting_mode)
        self.add_item(PropertyItem('Amb. Source', path + _p.ambient_source), lighting_mode)
        self.add_item(PropertyItem('Diff. Function', path + _p.diffuse_function), lighting_mode)
        self.add_item(PropertyItem('Attn. Function', path + _p.attenuation_function), lighting_mode)
        self.add_item(PropertyItem('Light Enable', path + _p.light_enable), lighting_mode)
        self.add_item(PropertyItem('Use Light 0', path + _p.use_light0), lighting_mode)
        self.add_item(PropertyItem('Use Light 1', path + _p.use_light1), lighting_mode)
        self.add_item(PropertyItem('Use Light 2', path + _p.use_light2), lighting_mode)
        self.add_item(PropertyItem('Use Light 3', path + _p.use_light3), lighting_mode)
        self.add_item(PropertyItem('Use Light 4', path + _p.use_light4), lighting_mode)
        self.add_item(PropertyItem('Use Light 5', path + _p.use_light5), lighting_mode)
        self.add_item(PropertyItem('Use Light 6', path + _p.use_light6), lighting_mode)
        self.add_item(PropertyItem('Use Light 7', path + _p.use_light7), lighting_mode)

    def add_texcoord_generator(self, label, path, parent):
        texcoord_generator = GroupItem([label, ''])
        self.add_item(texcoord_generator, parent)
        self.add_item(PropertyItem('Function', path + _p.function), texcoord_generator)
        self.add_item(PropertyItem('Source', path + _p.source), texcoord_generator)
        self.add_item(PropertyItem('Matrix', path + _p.matrix), texcoord_generator)

    def add_texture_matrix(self, label, path, parent):
        texture_matrix = GroupItem([label, ''])
        self.add_item(texture_matrix, parent)
        self.add_item(PropertyItem('Shape', path + _p.shape), texture_matrix)
        self.add_item(PropertyItem('Type', path + _p.matrix_type), texture_matrix)
        self.add_item(PropertyItem('Center S', path + _p.center_s), texture_matrix)
        self.add_item(PropertyItem('Center T', path + _p.center_t), texture_matrix)
        self.add_item(PropertyItem('Unknown 0', path + _p.unknown0), texture_matrix)
        self.add_item(PropertyItem('Scale S', path + _p.scale_s), texture_matrix)
        self.add_item(PropertyItem('Scale T', path + _p.scale_t), texture_matrix)
        self.add_item(PropertyItem('Rotation', path + _p.rotation), texture_matrix)
        self.add_item(PropertyItem('Translation S', path + _p.translation_s), texture_matrix)
        self.add_item(PropertyItem('Translation T', path + _p.translation_t), texture_matrix)
        self.add_item(PropertyItem('Projection Matrix', path + _p.projection_matrix), texture_matrix)

    def add_tev_mode(self, label, path, constant_path, parent):
        tev_mode = GroupItem([label, ''])
        self.add_item(tev_mode, parent)
        self.add_item(PropertyItem('Input A', path + _p.a), tev_mode)
        self.add_item(PropertyItem('Input B', path + _p.b), tev_mode)
        self.add_item(PropertyItem('Input C', path + _p.c), tev_mode)
        self.add_item(PropertyItem('Input D', path + _p.d), tev_mode)
        self.add_item(PropertyItem('Konst.', constant_path), tev_mode)
        self.add_item(PropertyItem('Function', path + _p.function), tev_mode)
        self.add_item(PropertyItem('Bias', path + _p.bias), tev_mode)
        self.add_item(PropertyItem('Scale', path + _p.scale), tev_mode)
        self.add_item(PropertyItem('Clamp', path + _p.clamp), tev_mode)
        self.add_item(PropertyItem('Output', path + _p.output), tev_mode)

    def add_tev_stage(self, label, path, parent):
        tev_stage = GroupItem([label, ''])
        self.add_item(tev_stage, parent)

        self.add_item(PropertyItem('Tex. Coord.', path + _p.texcoord), tev_stage)
        self.add_item(PropertyItem('Texture', path + _p.texture), tev_stage)
        self.add_item(PropertyItem('Color', path + _p.color), tev_stage)

        self.add_tev_mode('Color Combiner', path + _p.color_mode, path + _p.constant_color, tev_stage)
        self.add_tev_mode('Alpha Combiner', path + _p.alpha_mode, path + _p.constant_alpha, tev_stage)

        swap_mode = GroupItem(['Swap Mode', ''])
        self.add_item(swap_mode, tev_stage)
        self.add_item(PropertyItem('Color', path + _p.color_swap_table), swap_mode)
        self.add_item(PropertyItem('Texture', path + _p.texture_swap_table), swap_mode)

        indirect = GroupItem(['Indirect', ''])
        self.add_item(indirect, tev_stage)
        self.add_item(PropertyItem('Stage', path + _p.indirect_stage), indirect)
        self.add_item(PropertyItem('Format', path + _p.indirect_format), indirect)
        self.add_item(PropertyItem('Bias Comps.', path + _p.indirect_bias_components), indirect)
        self.add_item(PropertyItem('Matrix', path + _p.indirect_matrix), indirect)
        self.add_item(PropertyItem('Wrap S', path + _p.wrap_s), indirect)
        self.add_item(PropertyItem('Wrap T', path + _p.wrap_t), indirect)
        self.add_item(PropertyItem('Add Prev.', path + _p.add_previous_texcoord), indirect)
        self.add_item(PropertyItem('Use Orig. LOD', path + _p.use_original_lod), indirect)
        self.add_item(PropertyItem('Bump Alpha', path + _p.bump_alpha), indirect)

        self.add_item(PropertyItem('Unknown 0', path + _p.unknown0), tev_stage)
        self.add_item(PropertyItem('Unknown 1', path + _p.unknown1), tev_stage)

    def add_swap_table(self, label, path, parent):
        swap_table = GroupItem([label, ''])
        self.add_item(swap_table, parent)
        self.add_item(PropertyItem('R', path + _p.r), swap_table)
        self.add_item(PropertyItem('G', path + _p.g), swap_table)
        self.add_item(PropertyItem('B', path + _p.b), swap_table)
        self.add_item(PropertyItem('A', path + _p.a), swap_table)

    def add_indirect_stage(self, label, path, parent):
        indirect_stage = GroupItem([label, ''])
        self.add_item(indirect_stage, parent)
        self.add_item(PropertyItem('Tex. Coord.', path + _p.texcoord), indirect_stage)
        self.add_item(PropertyItem('Texture', path + _p.texture), indirect_stage)
        self.add_item(PropertyItem('Scale S', path + _p.scale_s), indirect_stage)
        self.add_item(PropertyItem('Scale T', path + _p.scale_t), indirect_stage)

    def update_channel_list(self):
        for i in range(self.channel_list.child_count):
            enable = i < self.view.channel_count
            self.channel_list.get_child(i).set_enabled(enable)
        left = self.get_item_index(self.channel_list)
        right = self.sibling(left.row(), self.columnCount(left) - 1, left)
        self.dataChanged.emit(left, right)

    def update_texcoord_generator_list(self):
        for i in range(self.texcoord_generator_list.child_count):
            enable = i < self.view.texcoord_generator_count
            self.texcoord_generator_list.get_child(i).set_enabled(enable)
        left = self.get_item_index(self.texcoord_generator_list)
        right = self.sibling(left.row(), self.columnCount(left) - 1, left)
        self.dataChanged.emit(left, right)

    def update_tev_stage_list(self):
        for i in range(self.tev_stage_list.child_count):
            enable = i < self.view.tev_stage_count
            self.tev_stage_list.get_child(i).set_enabled(enable)
        left = self.get_item_index(self.tev_stage_list)
        right = self.sibling(left.row(), self.columnCount(left) - 1, left)
        self.dataChanged.emit(left, right)

    def update_indirect_stage_list(self):
        for i in range(self.indirect_stage_list.child_count):
            enable = i < self.view.indirect_stage_count
            self.indirect_stage_list.get_child(i).set_enabled(enable)
        left = self.get_item_index(self.indirect_stage_list)
        right = self.sibling(left.row(), self.columnCount(left) - 1, left)
        self.dataChanged.emit(left, right)

    def handle_event(self, event, path):
        if isinstance(event, views.ValueChangedEvent):
            if path == +_p.channel_count:
                self.update_channel_list()
            elif path == +_p.texcoord_generator_count:
                self.update_texcoord_generator_list()
            elif path == +_p.tev_stage_count:
                self.update_tev_stage_list()
            elif path == +_p.indirect_stage_count:
                self.update_indirect_stage_list()


class ComboBoxDelegate(QtWidgets.QStyledItemDelegate):

    def get_item_data(self):
        return []

    def createEditor(self, parent, option, index):
        editor = QtWidgets.QComboBox(parent)
        for user_data in self.get_item_data():
            editor.addItem(self.displayText(user_data, option.locale), user_data)
        editor.activated.connect(self.on_editor_activated)
        return editor

    def setEditorData(self, editor, index):
        i = editor.findData(index.data(QtCore.Qt.EditRole))
        assert i != -1
        editor.setCurrentIndex(i)

    def setModelData(self, editor, model, index):
        model.setData(index, editor.currentData(), QtCore.Qt.EditRole)

    @QtCore.pyqtSlot(int)
    def on_editor_activated(self, index):
        self.commitData.emit(self.sender())


class CheckBoxDelegate(QtWidgets.QStyledItemDelegate):

    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        option.features &= ~QtWidgets.QStyleOptionViewItem.HasDisplay
        option.text = None
        option.features |= QtWidgets.QStyleOptionViewItem.HasCheckIndicator
        if index.data(QtCore.Qt.EditRole):
            option.checkState = QtCore.Qt.Checked
        else:
            option.checkState = QtCore.Qt.Unchecked

    def editorEvent(self, event, model, option, index):
        # Adapted from QStyledItemDelegate.editorEvent(). The model data is
        # changed when clicking the left mouse button inside the checkbox, or
        # when the space key or the select key is pressed while the item is
        # selected.
        #TODO Clicking anywhere, and then dragging the cursor inside the checkbox
        # and releasing also counts as a click.
        if not option.state & QtWidgets.QStyle.State_Enabled:
            return False
        if not index.flags() & QtCore.Qt.ItemIsEnabled:
            return False

        if option.widget is not None:
            style = option.widget.style()
        else:
            style = QtCore.QApplication.style()

        if event.type() == QtCore.QEvent.MouseButtonRelease:
            if event.button() != QtCore.Qt.LeftButton:
                return False
            option = QtWidgets.QStyleOptionViewItem(option)
            self.initStyleOption(option, index)
            check_rect = style.subElementRect(QtWidgets.QStyle.SE_ItemViewItemCheckIndicator, option, option.widget)
            if not check_rect.contains(event.pos()):
                return False
        elif event.type() == QtCore.QEvent.KeyPress:
            if event.key() not in {QtCore.Qt.Key_Space, QtCore.Qt.Key_Select}:
                return False
        else:
            return False

        value = index.data(QtCore.Qt.EditRole)
        model.setData(index, not value, QtCore.Qt.EditRole)
        return True

    def createEditor(self, parent, option, index):
        return None


class SpinBoxDelegate(QtWidgets.QStyledItemDelegate):

    def __init__(self, min, max, step=1):
        super().__init__()
        self.minimum = min
        self.maximum = max
        self.step = step

    def createEditor(self, parent, option, index):
        editor = QtWidgets.QSpinBox(parent)
        editor.setMinimum(self.minimum)
        editor.setMaximum(self.maximum)
        editor.setSingleStep(self.step)
        editor.valueChanged.connect(self.on_editor_valueChanged)
        return editor

    @QtCore.pyqtSlot(int)
    def on_editor_valueChanged(self, value):
        self.commitData.emit(self.sender())


class DoubleSpinBoxDelegate(QtWidgets.QStyledItemDelegate):

    def __init__(self, min, max, step=1, decimals=2):
        super().__init__()
        self.minimum = min
        self.maximum = max
        self.step = step
        self.decimals = decimals

    def displayText(self, value, locale):
        return super().displayText(f'{value:.{self.decimals}f}', locale)

    def createEditor(self, parent, option, index):
        editor = QtWidgets.QDoubleSpinBox(parent)
        editor.setMinimum(self.minimum)
        editor.setMaximum(self.maximum)
        editor.setSingleStep(self.step)
        editor.setDecimals(self.decimals)
        editor.valueChanged.connect(self.on_editor_valueChanged)
        return editor

    @QtCore.pyqtSlot(float)
    def on_editor_valueChanged(self, value):
        self.commitData.emit(self.sender())


class MatrixDelegate(QtWidgets.QStyledItemDelegate):

    def displayText(self, value, locale):
        text = '\n'.join(
            ', '.join(str(v) for v in c)
            for c in value
        )
        return super().displayText(text, locale)

    def sizeHint(self, option, index):
        option = QtWidgets.QStyleOptionViewItem(option)
        self.initStyleOption(option, index)
        return option.fontMetrics.size(0, option.text)

    def paint(self, painter, option, index):
        option = QtWidgets.QStyleOptionViewItem(option)
        self.initStyleOption(option, index)
        painter.drawText(option.rect, 0, option.text)

    def createEditor(self, parent, option, index):
        #TODO implement editing
        return None


class CountDelegate(ComboBoxDelegate):

    def __init__(self, max_count):
        super().__init__()
        self.max_count = max_count

    def get_item_data(self):
        return range(self.max_count + 1)


class EnumDelegate(ComboBoxDelegate):

    def __init__(self, enum_type):
        super().__init__()
        self.enum_type = enum_type

    def get_item_data(self):
        return self.enum_type

    def displayText(self, value, locale):
        return super().displayText(value.name, locale)


class DelegateDelegate(QtWidgets.QStyledItemDelegate):
    """Delegate that delegates to other delegates."""

    def __init__(self):
        super().__init__()
        self.delegate_table = {}

    def add_delegate(self, path, delegate):
        self.delegate_table[path] = delegate
        delegate.commitData.connect(self.commitData.emit)
        delegate.closeEditor.connect(self.closeEditor.emit)

    def sizeHint(self, option, index):
        path = index.data(PathRole)
        if path in self.delegate_table:
            return self.delegate_table[path].sizeHint(option, index)
        else:
            return super().sizeHint(option, index)

    def paint(self, painter, option, index):
        path = index.data(PathRole)
        if path in self.delegate_table:
            self.delegate_table[path].paint(painter, option, index)
        else:
            super().paint(painter, option, index)

    def editorEvent(self, event, model, option, index):
        path = index.data(PathRole)
        if path in self.delegate_table:
            return self.delegate_table[path].editorEvent(event, model, option, index)
        else:
            return super().editorEvent(event, model, option, index)

    def createEditor(self, parent, option, index):
        path = index.data(PathRole)
        if path in self.delegate_table:
            return self.delegate_table[path].createEditor(parent, option, index)
        else:
            return super().createEditor(parent, option, index)

    def setEditorData(self, editor, index):
        path = index.data(PathRole)
        if path in self.delegate_table:
            self.delegate_table[path].setEditorData(editor, index)
        else:
            super().setEditorData(editor, index)

    def setModelData(self, editor, model, index):
        path = index.data(PathRole)
        if path in self.delegate_table:
            self.delegate_table[path].setModelData(editor, model, index)
        else:
            super().setModelData(editor, model, index)


class AdvancedMaterialDialog(QtWidgets.QDialog):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ui = uic.loadUi(io.BytesIO(pkgutil.get_data(__package__, 'AdvancedMaterialDialog.ui')), self)

        self.delegate = DelegateDelegate()
        self.tree_view.setItemDelegate(self.delegate)

        self.add_delegate(+_p.channel_count, CountDelegate(2))
        for i in range(2):
            self.add_lighting_mode_delegates(+_p.channels[i].color_mode)
            self.add_lighting_mode_delegates(+_p.channels[i].alpha_mode)

        self.add_delegate(+_p.texcoord_generator_count, CountDelegate(8))
        for i in range(8):
            self.add_texcoord_generator_delegates(+_p.texcoord_generators[i])

        for i in range(10):
            self.add_texture_matrix_delegates(+_p.texture_matrices[i])

        self.add_delegate(+_p.tev_stage_count, CountDelegate(16))
        for i in range(16):
            self.add_tev_stage_delegates(+_p.tev_stages[i])

        for i in range(4):
            self.add_swap_table_delegates(+_p.swap_tables[i])

        self.add_delegate(+_p.indirect_stage_count, CountDelegate(4))
        for i in range(4):
            self.add_indirect_stage_delegates(+_p.indirect_stages[i])

    def add_delegate(self, path, delegate):
        self.delegate.add_delegate(path, delegate)

    def add_lighting_mode_delegates(self, path):
        self.add_delegate(path + _p.material_source, EnumDelegate(gx.ChannelSource))
        self.add_delegate(path + _p.ambient_source, EnumDelegate(gx.ChannelSource))
        self.add_delegate(path + _p.diffuse_function, EnumDelegate(gx.DiffuseFunction))
        self.add_delegate(path + _p.attenuation_function, EnumDelegate(gx.AttenuationFunction))
        self.add_delegate(path + _p.light_enable, CheckBoxDelegate())
        self.add_delegate(path + _p.use_light0, CheckBoxDelegate())
        self.add_delegate(path + _p.use_light1, CheckBoxDelegate())
        self.add_delegate(path + _p.use_light2, CheckBoxDelegate())
        self.add_delegate(path + _p.use_light3, CheckBoxDelegate())
        self.add_delegate(path + _p.use_light4, CheckBoxDelegate())
        self.add_delegate(path + _p.use_light5, CheckBoxDelegate())
        self.add_delegate(path + _p.use_light6, CheckBoxDelegate())
        self.add_delegate(path + _p.use_light7, CheckBoxDelegate())

    def add_texcoord_generator_delegates(self, path):
        self.add_delegate(path + _p.function, EnumDelegate(gx.TexCoordFunction))
        self.add_delegate(path + _p.source, EnumDelegate(gx.TexCoordSource))
        self.add_delegate(path + _p.matrix, EnumDelegate(gx.TextureMatrix))

    def add_texture_matrix_delegates(self, path):
        float_delegate = DoubleSpinBoxDelegate(min=-1000, max=1000, step=0.1)
        self.add_delegate(path + _p.shape, EnumDelegate([gx.TG_MTX3x4, gx.TG_MTX2x4]))
        self.add_delegate(path + _p.matrix_type, SpinBoxDelegate(min=0, max=255))
        self.add_delegate(path + _p.center_s, float_delegate)
        self.add_delegate(path + _p.center_t, float_delegate)
        self.add_delegate(path + _p.unknown0, float_delegate)
        self.add_delegate(path + _p.scale_s, float_delegate)
        self.add_delegate(path + _p.scale_t, float_delegate)
        self.add_delegate(path + _p.rotation, DoubleSpinBoxDelegate(min=-180, max=180))
        self.add_delegate(path + _p.translation_s, float_delegate)
        self.add_delegate(path + _p.translation_t, float_delegate)
        self.add_delegate(path + _p.projection_matrix, MatrixDelegate())

    def add_tev_stage_delegates(self, path):
        self.add_delegate(path + _p.texcoord, EnumDelegate(gx.TexCoord))
        self.add_delegate(path + _p.texture, EnumDelegate(gx.Texture))
        self.add_delegate(path + _p.color, EnumDelegate(gx.Channel))

        self.add_delegate(path + _p.color_mode.a, EnumDelegate(gx.ColorInput))
        self.add_delegate(path + _p.color_mode.b, EnumDelegate(gx.ColorInput))
        self.add_delegate(path + _p.color_mode.c, EnumDelegate(gx.ColorInput))
        self.add_delegate(path + _p.color_mode.d, EnumDelegate(gx.ColorInput))
        self.add_delegate(path + _p.color_mode.function, EnumDelegate(gx.TevFunction))
        self.add_delegate(path + _p.color_mode.bias, EnumDelegate(gx.TevBias))
        self.add_delegate(path + _p.color_mode.scale, EnumDelegate(gx.TevScale))
        self.add_delegate(path + _p.color_mode.clamp, CheckBoxDelegate())
        self.add_delegate(path + _p.color_mode.output, EnumDelegate(gx.TevColor))
        self.add_delegate(path + _p.constant_color, EnumDelegate(gx.ConstantColor))

        self.add_delegate(path + _p.alpha_mode.a, EnumDelegate(gx.AlphaInput))
        self.add_delegate(path + _p.alpha_mode.b, EnumDelegate(gx.AlphaInput))
        self.add_delegate(path + _p.alpha_mode.c, EnumDelegate(gx.AlphaInput))
        self.add_delegate(path + _p.alpha_mode.d, EnumDelegate(gx.AlphaInput))
        self.add_delegate(path + _p.alpha_mode.function, EnumDelegate(gx.TevFunction))
        self.add_delegate(path + _p.alpha_mode.bias, EnumDelegate(gx.TevBias))
        self.add_delegate(path + _p.alpha_mode.scale, EnumDelegate(gx.TevScale))
        self.add_delegate(path + _p.alpha_mode.clamp, CheckBoxDelegate())
        self.add_delegate(path + _p.alpha_mode.output, EnumDelegate(gx.TevColor))
        self.add_delegate(path + _p.constant_alpha, EnumDelegate(gx.ConstantAlpha))

        self.add_delegate(path + _p.color_swap_table, EnumDelegate(gx.SwapTable))
        self.add_delegate(path + _p.texture_swap_table, EnumDelegate(gx.SwapTable))

        self.add_delegate(path + _p.indirect_stage, EnumDelegate(gx.IndirectStage))
        self.add_delegate(path + _p.indirect_format, EnumDelegate(gx.IndirectFormat))
        self.add_delegate(path + _p.indirect_bias_components, EnumDelegate(gx.IndirectBiasComponents))
        self.add_delegate(path + _p.indirect_matrix, EnumDelegate(gx.IndirectMatrix))
        self.add_delegate(path + _p.wrap_s, EnumDelegate(gx.IndirectWrap))
        self.add_delegate(path + _p.wrap_t, EnumDelegate(gx.IndirectWrap))
        self.add_delegate(path + _p.add_previous_texcoord, CheckBoxDelegate())
        self.add_delegate(path + _p.use_original_lod, CheckBoxDelegate())
        self.add_delegate(path + _p.bump_alpha, EnumDelegate(gx.IndirectBumpAlpha))

        self.add_delegate(path + _p.unknown0, SpinBoxDelegate(min=0, max=255))
        self.add_delegate(path + _p.unknown1, SpinBoxDelegate(min=0, max=255))

    def add_swap_table_delegates(self, path):
        delegate = EnumDelegate(gx.ColorComponent)
        self.add_delegate(path + _p.r, delegate)
        self.add_delegate(path + _p.g, delegate)
        self.add_delegate(path + _p.b, delegate)
        self.add_delegate(path + _p.a, delegate)

    def add_indirect_stage_delegates(self, path):
        self.add_delegate(path + _p.texcoord, EnumDelegate(gx.TexCoord))
        self.add_delegate(path + _p.texture, EnumDelegate(gx.Texture))
        self.add_delegate(path + _p.scale_s, EnumDelegate(gx.IndirectScale))
        self.add_delegate(path + _p.scale_t, EnumDelegate(gx.IndirectScale))

    def setMaterial(self, material):
        self.tree_view.setModel(MaterialAdaptor(material))
        self.tree_view.setColumnWidth(0, 200)

    def clear(self):
        self.tree_view.setModel(None)

