import io
from PyQt5 import QtWidgets


class InfoDialog(QtWidgets.QDialog):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setWindowTitle('Info Dialog')

        self.info = QtWidgets.QPlainTextEdit()
        self.info.setReadOnly(True)

        self.button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        self.layout = QtWidgets.QVBoxLayout()
        self.layout.setContentsMargins(4, 4, 4, 4)
        self.layout.addWidget(self.info)
        self.layout.addWidget(self.button_box)
        self.setLayout(self.layout)

    def _write_vertex_array_info(self, stream, model):
        arrays = []
        if model.position_array is not None:
            arrays.append(model.position_array)
        if model.normal_array is not None:
            arrays.append(model.normal_array)
        arrays.extend(filter(None.__ne__, model.color_arrays))
        arrays.extend(filter(None.__ne__, model.texcoord_arrays))

        stream.write('Vertex Arrays\n')
        stream.write('====================\n')
        stream.write('\n')

        total_byte_count = 0

        for array in arrays:
            stream.write(f'Attribute: {array.attribute.name}\n')
            stream.write(f'Component Type: {array.component_type.name}\n')
            stream.write(f'Component Count: {array.component_count.name}\n')
            stream.write(f'Scale Exponent: {array.scale_exponent}\n')
            stream.write(f'Length: {len(array)}\n')
            stream.write(f'Bytes: {array.nbytes}\n')
            stream.write('\n')
            total_byte_count += array.nbytes

        stream.write('Total\n')
        stream.write(f'Bytes: {total_byte_count}\n')
        stream.write('\n')

    def _write_shape_info(self, stream, model):
        stream.write('Shapes\n')
        stream.write('====================\n')
        stream.write('\n')

        total_batch_count = 0
        total_primitive_count = 0
        total_vertex_count = 0
        total_byte_count = 0

        for i, shape in enumerate(model.shapes):
            batch_count = len(shape.batches)
            primitive_count = sum(len(batch.primitives) for batch in shape.batches)
            vertex_count = sum(len(primitive.vertices) for primitive in shape.primitives)
            byte_count = sum(3 + primitive.vertices.nbytes for primitive in shape.primitives)

            stream.write(f'Shape {i}\n')
            for descriptor in shape.attribute_descriptors:
                stream.write(f'{descriptor.attribute.name}: {descriptor.input_type.name}\n')
            stream.write(f'Batches: {batch_count}\n')
            stream.write(f'Primitives: {primitive_count}\n')
            stream.write(f'Vertices: {vertex_count}\n')
            stream.write(f'Bytes: {byte_count}\n')
            stream.write('\n')

            total_batch_count += batch_count
            total_primitive_count += primitive_count
            total_vertex_count += vertex_count
            total_byte_count += byte_count

        stream.write('Total\n')
        stream.write(f'Batches: {total_batch_count}\n')
        stream.write(f'Primitives: {total_primitive_count}\n')
        stream.write(f'Vertices: {total_vertex_count}\n')
        stream.write(f'Bytes: {total_byte_count}\n')
        stream.write('\n')

    def _write_texture_info(self, stream, model):
        stream.write('Textures\n')
        stream.write('====================\n')
        stream.write('\n')

        seen_image_ids = set()
        seen_palette_ids = set()
        total_image_byte_count = 0
        total_palette_byte_count = 0

        for texture in model.textures:
            image_byte_count = sum(image.nbytes for image in texture.images)
            stream.write(f'{texture.name}\n')
            stream.write(f'Image Format: {texture.image_format.name}\n')
            stream.write(f'Image Size: {texture.width} x {texture.height}\n')
            stream.write(f'Image Levels: {len(texture.images)}\n')
            if id(texture.images) in seen_image_ids:
                stream.write(f'Image Bytes: {image_byte_count} (shared)\n')
            else:
                stream.write(f'Image Bytes: {image_byte_count}\n')
                total_image_byte_count += image_byte_count
                seen_image_ids.add(id(texture.images))
            if texture.palette is not None:
                stream.write(f'Palette Format: {texture.palette.palette_format.name}\n')
                stream.write(f'Palette Size: {len(texture.palette)}\n')
                if id(texture.palette) in seen_palette_ids:
                    stream.write(f'Palette Bytes: {texture.palette.nbytes} (shared)\n')
                else:
                    stream.write(f'Palette Bytes: {texture.palette.nbytes}\n')
                    total_palette_byte_count += texture.palette.nbytes
                    seen_palette_ids.add(id(texture.palette))
            stream.write('\n')

        stream.write('Total\n')
        stream.write(f'Image Bytes: {total_image_byte_count}\n')
        stream.write(f'Palette Bytes: {total_palette_byte_count}\n')
        stream.write('\n')

    def setModel(self, model):
        stream = io.StringIO()
        self._write_vertex_array_info(stream, model)
        self._write_shape_info(stream, model)
        self._write_texture_info(stream, model)
        self.info.setPlainText(stream.getvalue())

    def clear():
        self.info.clear()

