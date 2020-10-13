from enum import Enum
from btypes.big_endian import *
import logging

logger = logging.getLogger(__name__)


class Header(Struct):
    magic = ByteString(4)
    section_size = uint32
    unknown0 = uint16 # noclip.website: load flags
    __padding__ = Padding(2)
    shape_batch_count = uint32
    vertex_position_count = uint32
    scene_graph_offset = uint32

    def __init__(self):
        self.magic = b'INF1'

    @classmethod
    def unpack(cls, stream):
        header = super().unpack(stream)
        if header.magic != b'INF1':
            raise FormatError(f'invalid magic: {header.magic}')
        if header.unknown0 not in {0, 1, 2}:
            logger.warning('unexpected unknown0 value: %s', header.unknown0)
        return header


class NodeType(Enum):
    END_GRAPH = 0x00
    BEGIN_CHILDREN = 0x01
    END_CHILDREN = 0x02
    JOINT = 0x10
    MATERIAL = 0x11
    SHAPE = 0x12


class Node(Struct):
    node_type = EnumConverter(uint16, NodeType)
    index = uint16

    def __init__(self, node_type, index):
        self.node_type = node_type
        self.index = index
        self.children = []

    @classmethod
    def unpack(cls, stream):
        node = super().unpack(stream)
        node.children = []
        return node


class SceneGraph:

    def __init__(self):
        self.unknown0 = 0
        self.children = []


class SectionData:

    def __init__(self, scene_graph, shape_batch_count, vertex_position_count):
        self.scene_graph = scene_graph
        self.shape_batch_count = shape_batch_count
        self.vertex_position_count = vertex_position_count


def pack_nodes(stream, nodes):
    for node in nodes:
        Node.pack(stream, node)
        if node.children:
            Node.pack(stream, Node(NodeType.BEGIN_CHILDREN, 0))
            pack_nodes(stream, node.children)
            Node.pack(stream, Node(NodeType.END_CHILDREN, 0))


def unpack_nodes(stream, end_node_type=NodeType.END_CHILDREN):
    nodes = []
    while True:
        node = Node.unpack(stream)
        if node.node_type == end_node_type:
            return nodes
        elif node.node_type == NodeType.BEGIN_CHILDREN:
            nodes[-1].children = unpack_nodes(stream)
        else:
            nodes.append(node)


def pack(stream, scene_graph, shape_batch_count, vertex_position_count):
    base = stream.tell()
    header = Header()
    header.unknown0 = scene_graph.unknown0
    header.shape_batch_count = shape_batch_count
    header.vertex_position_count = vertex_position_count
    stream.write(b'\x00'*Header.sizeof())

    header.scene_graph_offset = stream.tell() - base
    pack_nodes(stream, scene_graph.children)
    Node.pack(stream, Node(NodeType.END_GRAPH, 0))

    align(stream, 0x20)
    header.section_size = stream.tell() - base
    stream.seek(base)
    Header.pack(stream, header)
    stream.seek(base + header.section_size)


def unpack(stream):
    base = stream.tell()
    header = Header.unpack(stream)

    stream.seek(base + header.scene_graph_offset)
    scene_graph = SceneGraph()
    scene_graph.unknown0 = header.unknown0
    scene_graph.children = unpack_nodes(stream, NodeType.END_GRAPH)

    stream.seek(base + header.section_size)
    return SectionData(
        scene_graph=scene_graph,
        shape_batch_count=header.shape_batch_count,
        vertex_position_count=header.vertex_position_count
    )

