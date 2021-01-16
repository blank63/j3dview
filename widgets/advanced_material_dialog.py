from dataclasses import dataclass
import io
import pkgutil
from PyQt5 import QtCore, QtWidgets, uic
import gx
from modelview.path import Path, PATH_BUILDER as _p
from widgets.view_form import (
    Item,
    GroupItem,
    ItemModelAdaptor,
    DelegateDelegate,
    CountDelegate,
    EnumDelegate,
    CheckBoxDelegate,
    SpinBoxDelegate,
    DoubleSpinBoxDelegate,
    MatrixDelegate
)


TypeTagRole = QtCore.Qt.UserRole


@dataclass(frozen=True)
class BoolTag:
    pass


@dataclass(frozen=True)
class IntTag:
    min: int
    max: int


@dataclass(frozen=True)
class FloatTag:
    min: float
    max: float
    step: float = 1


@dataclass(frozen=True)
class CountTag:
    max: int


@dataclass(frozen=True)
class EnumTag:
    values: tuple

    @staticmethod
    def from_iterable(values):
        return EnumTag(tuple(values))


@dataclass(frozen=True)
class MatrixTag:
    pass


_bool = BoolTag
_int = IntTag
_float = FloatTag
_count = CountTag
_enum = EnumTag.from_iterable
_matrix = MatrixTag


class PropertyItem(Item):

    def __init__(self, label, path, type_tag):
        super().__init__()
        self.label = label
        self.path = path
        self.type_tag = type_tag
        self.triggers = frozenset((path,))

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

    def get_data(self, column, role):
        if column == 0:
            if role == QtCore.Qt.DisplayRole:
                return self.label
            return QtCore.QVariant()
        if column == 1:
            if role in {QtCore.Qt.DisplayRole, QtCore.Qt.EditRole}:
                return self.path.get_value(self.model.view)
            if role == TypeTagRole:
                return self.type_tag
            return QtCore.QVariant()
        assert False

    def set_data(self, column, value, role):
        if column != 1:
            return False
        if role != QtCore.Qt.EditRole:
            return False
        self.model.commitViewValue.emit(self.label, self.path, value)
        return True

    def handle_event(self, event, path):
        self.model.item_data_changed(self)


class ListWithCountItem(GroupItem):

    def __init__(self, label, count_path):
        super().__init__([label, ''])
        self.count_path = count_path
        self.triggers = frozenset((count_path,))

    def update(self):
        count = self.count_path.get_value(self.model.view)
        for i in range(self.child_count):
            enable = i < count
            self.get_child(i).set_enabled(enable)
        self.model.item_data_changed(self)

    def handle_event(self, event, path):
        self.update()


class MaterialAdaptor(ItemModelAdaptor):

    def __init__(self, material):
        super().__init__(material)
        self.set_header_labels(['Property', 'Value'])

        self.add_channel_list()
        self.add_texcoord_generator_list()
        self.add_texture_matrix_list()
        self.add_tev_stage_list()
        self.add_swap_table_list()
        self.add_indirect_stage_list()
        self.add_indirect_matrix_list()

    def _group(self, label, parent=None):
        item = GroupItem([label, ''])
        self.add_item(item, parent)
        return item

    def _listwc(self, label, count_path, parent=None):
        item = ListWithCountItem(label, count_path)
        self.add_item(item, parent)
        return item

    def _property(self, label, path, type_tag, parent=None):
        item = PropertyItem(label, path, type_tag)
        self.add_item(item, parent)
        return item

    def add_lighting_mode(self, label, path, parent):
        base = self._group(label, parent)
        self._property('Mat. Source', path + _p.material_source, _enum(gx.ChannelSource), base)
        self._property('Amb. Source', path + _p.ambient_source, _enum(gx.ChannelSource), base)
        self._property('Diff. Function', path + _p.diffuse_function, _enum(gx.DiffuseFunction), base)
        self._property('Attn. Function', path + _p.attenuation_function, _enum(gx.AttenuationFunction), base)
        self._property('Light Enable', path + _p.light_enable, _bool(), base)
        for i in range(8):
            self._property(f'Use Light {i}', path + _p.use_light[i], _bool(), base)

    def add_channel_list(self):
        self._property('Num. Channels', +_p.channel_count, _count(2))
        base = self._listwc('Channels', +_p.channel_count)
        for i in range(2):
            channel = self._group(f'Channel {i}', base)
            self.add_lighting_mode('Color', +_p.channels[i].color_mode, channel)
            self.add_lighting_mode('Alpha', +_p.channels[i].alpha_mode, channel)
        base.update()

    def add_texcoord_generator(self, label, path, parent):
        base = self._group(label, parent)
        self._property('Function', path + _p.function, _enum(gx.TexCoordFunction), base)
        self._property('Source', path + _p.source, _enum(gx.TexCoordSource), base)
        self._property('Matrix', path + _p.matrix, _enum(gx.TextureMatrix), base)

    def add_texcoord_generator_list(self):
        self._property('Num. Tex. Gens.', +_p.texcoord_generator_count, _count(8))
        base = self._listwc('Tex. Gens.', +_p.texcoord_generator_count)
        for i in range(8):
            self.add_texcoord_generator(f'Tex. Gen. {i}', +_p.texcoord_generators[i], base)
        base.update()

    def add_texture_matrix(self, label, path, parent):
        base = self._group(label, parent)
        float_tag = _float(min=-1000, max=1000, step=0.1)
        self._property('Shape', path + _p.shape, _enum([gx.TG_MTX3x4, gx.TG_MTX2x4]), base)
        self._property('Type', path + _p.matrix_type, _int(min=0, max=255), base)
        self._property('Center S', path + _p.center_s, float_tag, base)
        self._property('Center T', path + _p.center_t, float_tag, base)
        self._property('Unknown 0', path + _p.unknown0, float_tag, base)
        self._property('Scale S', path + _p.scale_s, float_tag, base)
        self._property('Scale T', path + _p.scale_t, float_tag, base)
        self._property('Rotation', path + _p.rotation, _float(min=-180, max=180), base)
        self._property('Translation S', path + _p.translation_s, float_tag, base)
        self._property('Translation T', path + _p.translation_t, float_tag, base)
        self._property('Projection Matrix', path + _p.projection_matrix, _matrix(), base)

    def add_texture_matrix_list(self):
        base = self._group('Texture Matrices')
        for i in range(10):
            self.add_texture_matrix(f'Texture Matrix {i}', +_p.texture_matrices[i], base)

    def add_tev_stage(self, label, path, parent):
        base = self._group(label, parent)

        self._property('Tex. Coord.', path + _p.texcoord, _enum(gx.TexCoord), base)
        self._property('Texture', path + _p.texture, _enum(gx.Texture), base)
        self._property('Color', path + _p.color, _enum(gx.Channel), base)

        color_mode = self._group('Color Combiner', base)
        self._property('Input A', path + _p.color_mode.a, _enum(gx.ColorInput), color_mode)
        self._property('Input B', path + _p.color_mode.b, _enum(gx.ColorInput), color_mode)
        self._property('Input C', path + _p.color_mode.c, _enum(gx.ColorInput), color_mode)
        self._property('Input D', path + _p.color_mode.d, _enum(gx.ColorInput), color_mode)
        self._property('Konst.', path + _p.constant_color, _enum(gx.ConstantColor), color_mode)
        self._property('Function', path + _p.color_mode.function, _enum(gx.TevFunction), color_mode)
        self._property('Bias', path + _p.color_mode.bias, _enum(gx.TevBias), color_mode)
        self._property('Scale', path + _p.color_mode.scale, _enum(gx.TevScale), color_mode)
        self._property('Clamp', path + _p.color_mode.clamp, _bool(), color_mode)
        self._property('Output', path + _p.color_mode.output, _enum(gx.TevColor), color_mode)

        alpha_mode = self._group('Alpha Combiner', base)
        self._property('Input A', path + _p.alpha_mode.a, _enum(gx.AlphaInput), alpha_mode)
        self._property('Input B', path + _p.alpha_mode.b, _enum(gx.AlphaInput), alpha_mode)
        self._property('Input C', path + _p.alpha_mode.c, _enum(gx.AlphaInput), alpha_mode)
        self._property('Input D', path + _p.alpha_mode.d, _enum(gx.AlphaInput), alpha_mode)
        self._property('Konst.', path + _p.constant_alpha, _enum(gx.ConstantAlpha), alpha_mode)
        self._property('Function', path + _p.alpha_mode.function, _enum(gx.TevFunction), alpha_mode)
        self._property('Bias', path + _p.alpha_mode.bias, _enum(gx.TevBias), alpha_mode)
        self._property('Scale', path + _p.alpha_mode.scale, _enum(gx.TevScale), alpha_mode)
        self._property('Clamp', path + _p.alpha_mode.clamp, _bool(), alpha_mode)
        self._property('Output', path + _p.alpha_mode.output, _enum(gx.TevColor), alpha_mode)

        swap_mode = self._group('Swap Mode', base)
        self._property('Color', path + _p.color_swap_table, _enum(gx.SwapTable), swap_mode)
        self._property('Texture', path + _p.texture_swap_table, _enum(gx.SwapTable), swap_mode)

        indirect = self._group('Indirect', base)
        self._property('Stage', path + _p.indirect_stage, _enum(gx.IndirectStage), indirect)
        self._property('Format', path + _p.indirect_format, _enum(gx.IndirectFormat), indirect)
        self._property('Bias Comps.', path + _p.indirect_bias_components, _enum(gx.IndirectBiasComponents), indirect)
        self._property('Matrix', path + _p.indirect_matrix, _enum(gx.IndirectMatrix), indirect)
        self._property('Wrap S', path + _p.wrap_s, _enum(gx.IndirectWrap), indirect)
        self._property('Wrap T', path + _p.wrap_t, _enum(gx.IndirectWrap), indirect)
        self._property('Add Prev.', path + _p.add_previous_texcoord, _bool(), indirect)
        self._property('Use Orig. LOD', path + _p.use_original_lod, _bool(), indirect)
        self._property('Bump Alpha', path + _p.bump_alpha, _enum(gx.IndirectBumpAlpha), indirect)

        self._property('Unknown 0', path + _p.unknown0, _int(min=0, max=255), base)
        self._property('Unknown 1', path + _p.unknown1, _int(min=0, max=255), base)

    def add_tev_stage_list(self):
        self._property('Num. TEV Stages', +_p.tev_stage_count, _count(16))
        base = self._listwc('TEV Stages', +_p.tev_stage_count)
        for i in range(16):
            self.add_tev_stage(f'TEV Stage {i}', +_p.tev_stages[i], base)
        base.update()

    def add_swap_table(self, label, path, parent):
        base = self._group(label, parent)
        self._property('R', path + _p.r, _enum(gx.ColorComponent), base)
        self._property('G', path + _p.g, _enum(gx.ColorComponent), base)
        self._property('B', path + _p.b, _enum(gx.ColorComponent), base)
        self._property('A', path + _p.a, _enum(gx.ColorComponent), base)

    def add_swap_table_list(self):
        base = self._group('Swap Tables')
        for i in range(4):
            self.add_swap_table(f'Swap Table {i}', +_p.swap_tables[i], base)

    def add_indirect_stage(self, label, path, parent):
        base = self._group(label, parent)
        self._property('Tex. Coord.', path + _p.texcoord, _enum(gx.TexCoord), base)
        self._property('Texture', path + _p.texture, _enum(gx.Texture), base)
        self._property('Scale S', path + _p.scale_s, _enum(gx.IndirectScale), base)
        self._property('Scale T', path + _p.scale_t, _enum(gx.IndirectScale), base)

    def add_indirect_stage_list(self):
        self._property('Num. Indirect Stages', +_p.indirect_stage_count, _count(4))
        base = self._listwc('Indirect Stages', +_p.indirect_stage_count)
        for i in range(4):
            self.add_indirect_stage(f'Indirect Stage {i}', +_p.indirect_stages[i], base)
        base.update()

    def add_indirect_matrix(self, label, path, parent):
        base = self._group(label, parent)
        self._property('Significand Matrix', path + _p.significand_matrix, _matrix(), base)
        self._property('Scale Exponent', path + _p.scale_exponent, _int(min=-128, max=127), base)

    def add_indirect_matrix_list(self):
        base = self._group('Indirect Matrices')
        for i in range(3):
            self.add_indirect_matrix(f'Indirect Matrix {i}', +_p.indirect_matrices[i], base)


class Delegate(DelegateDelegate):

    def __init__(self):
        super().__init__()
        self.delegate_table = {}

    def create_delegate(self, type_tag):
        if isinstance(type_tag, BoolTag):
            return CheckBoxDelegate()
        if isinstance(type_tag, IntTag):
            return SpinBoxDelegate(min=type_tag.min, max=type_tag.max)
        if isinstance(type_tag, FloatTag):
            return DoubleSpinBoxDelegate(min=type_tag.min, max=type_tag.max, step=type_tag.step)
        if isinstance(type_tag, CountTag):
            return CountDelegate(type_tag.max)
        if isinstance(type_tag, EnumTag):
            return EnumDelegate(type_tag.values)
        if isinstance(type_tag, MatrixTag):
            return MatrixDelegate()
        assert False

    def get_delegate(self, item):
        type_tag = item.data(TypeTagRole)
        if type_tag is None:
            return super().get_delegate(item)
        delegate = self.delegate_table.get(type_tag)
        if delegate is None:
            delegate = self.create_delegate(type_tag)
            delegate.commitData.connect(self.commitData.emit)
            delegate.closeEditor.connect(self.closeEditor.emit)
            self.delegate_table[type_tag] = delegate
        return delegate


class AdvancedMaterialDialog(QtWidgets.QDialog):

    commitViewValue = QtCore.pyqtSignal(str, Path, object)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ui = uic.loadUi(io.BytesIO(pkgutil.get_data(__package__, 'AdvancedMaterialDialog.ui')), self)
        self.delegate = Delegate()
        self.tree_view.setItemDelegate(self.delegate)

    def setMaterial(self, material):
        adaptor = MaterialAdaptor(material)
        adaptor.commitViewValue.connect(self.commitViewValue.emit)
        self.tree_view.setModel(adaptor)
        self.tree_view.setColumnWidth(0, 200)

    def clear(self):
        self.tree_view.setModel(None)

