# tim_operations.py
import os
import struct
import numpy as np
from PIL import Image
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import QGraphicsPixmapItem

def read_tim(file_path):
    """
    Reads a TIM file and returns a dictionary with its data.
    """
    with open(file_path, 'rb') as raw_file:
        header_id = raw_file.read(4)
        format_flag = raw_file.read(4)
        if header_id != b'\x10\x00\x00\x00':
            raise ValueError("Invalid TIM header")
        if format_flag not in [b'\x08\x00\x00\x00', b'\x09\x00\x00\x00']:
            raise ValueError("Unsupported TIM format")
        clut_bnum = struct.unpack('<I', raw_file.read(4))[0]
        clut_coord_x = struct.unpack('<H', raw_file.read(2))[0]
        clut_coord_y = struct.unpack('<H', raw_file.read(2))[0]
        clut_size_x = struct.unpack('<H', raw_file.read(2))[0]
        clut_size_y = struct.unpack('<H', raw_file.read(2))[0]
        clut_data_length = clut_bnum - 12
        clut_data = raw_file.read(clut_data_length)
        pixel_bnum = struct.unpack('<I', raw_file.read(4))[0]
        pixel_coord_x = struct.unpack('<H', raw_file.read(2))[0]
        pixel_coord_y = struct.unpack('<H', raw_file.read(2))[0]
        pixel_data_width = struct.unpack('<H', raw_file.read(2))[0]
        pixel_data_height = struct.unpack('<H', raw_file.read(2))[0]
        if format_flag == b'\x08\x00\x00\x00':
            pixel_data_width *= 4
        elif format_flag == b'\x09\x00\x00\x00':
            pixel_data_width *= 2
        pixel_data_length = pixel_bnum - 12
        pixel_data = raw_file.read(pixel_data_length)
    return {
        "file_name": os.path.basename(file_path),
        "file_path": file_path,
        "header_id": header_id,
        "format_flag": format_flag,
        "clut_bnum": clut_bnum,
        "clut_data": clut_data,
        "clut_coord_x": clut_coord_x,
        "clut_coord_y": clut_coord_y,
        "clut_size_x": clut_size_x,
        "clut_size_y": clut_size_y,
        "pixel_bnum": pixel_bnum,
        "pixel_coord_x": pixel_coord_x,
        "pixel_coord_y": pixel_coord_y,
        "pixel_data_width": pixel_data_width,
        "pixel_data_height": pixel_data_height,
        "pixel_data": pixel_data
    }

def write_tim_file(tim_data_dict, out_path):
    """
    Zapisuje plik TIM na podstawie danych zawartych w słowniku tim_data_dict.
    Oczekiwane klucze w tim_data_dict:
      - header_id: bajtowy ciąg (np. b'\x10\x00\x00\x00')
      - tim_format: bajtowy ciąg określający format TIM
      - new_clut_bnum: int, długość sekcji CLUT (nagłówek CLUT)
      - clut_coord_x, clut_coord_y: int, współrzędne CLUT
      - clut_size_x, clut_size_y: int, rozmiar CLUT (np. 16x1 dla 4-bit lub 256x1 dla 8-bit)
      - common_clut: bajtowy ciąg z danymi palety
      - new_pixel_bnum: int, długość sekcji danych pikselowych (nagłówek danych pikselowych)
      - pixel_coord_x, pixel_coord_y: int, pozycja pikseli
      - stored_width_value: int, szerokość obrazu w jednostkach TIM
      - height: int, wysokość obrazu
      - new_pixel_data: bajtowy ciąg z danymi pikselowymi
    """
    import struct
    with open(out_path, "wb") as f:
        f.write(tim_data_dict["header_id"])
        f.write(tim_data_dict["tim_format"])
        f.write(struct.pack("<I", tim_data_dict["new_clut_bnum"]))
        f.write(struct.pack("<HH", tim_data_dict["clut_coord_x"], tim_data_dict["clut_coord_y"]))
        f.write(struct.pack("<HH", tim_data_dict["clut_size_x"], tim_data_dict["clut_size_y"]))
        f.write(tim_data_dict["common_clut"])
        f.write(struct.pack("<I", tim_data_dict["new_pixel_bnum"]))
        f.write(struct.pack("<HH", tim_data_dict["pixel_coord_x"], tim_data_dict["pixel_coord_y"]))
        f.write(struct.pack("<H", tim_data_dict["stored_width_value"]))
        f.write(struct.pack("<H", tim_data_dict["height"]))
        f.write(tim_data_dict["new_pixel_data"])


class Tim_Object:
    """
    Handles TIM file operations: decoding and converting to a graphics item.
    """
    def __init__(self, tim_data):
        self.tim_file_name = tim_data["file_name"]
        self.tim_file_path = tim_data["file_path"]
        self.header_id = tim_data["header_id"]
        self.format_flag = tim_data["format_flag"]
        self.clut_bnum = tim_data["clut_bnum"]
        self.clut_data = tim_data["clut_data"]
        self.clut_coord_x = tim_data["clut_coord_x"]
        self.clut_coord_y = tim_data["clut_coord_y"]
        self.clut_size_x = tim_data["clut_size_x"]
        self.clut_size_y = tim_data["clut_size_y"]
        self.clut_data_length = len(tim_data["clut_data"])
        self.pixel_bnum = tim_data["pixel_bnum"]
        self.pixel_coord_x = tim_data["pixel_coord_x"]
        self.pixel_coord_y = tim_data["pixel_coord_y"]
        self.pixel_data_width = tim_data["pixel_data_width"]
        self.pixel_data_height = tim_data["pixel_data_height"]
        self.pixel_data_length = len(tim_data["pixel_data"])
        self.pixel_data = tim_data["pixel_data"]
        self.pil_image = None

    def decode(self):
        """
        Decodes TIM data into a QPixmap.
        """
        clut_raw = np.frombuffer(self.clut_data, dtype=np.uint16)
        clut_rgb = [((color & 0x1F) << 3, ((color >> 5) & 0x1F) << 3, ((color >> 10) & 0x1F) << 3)
                    for color in clut_raw]
        clut = np.array(clut_rgb, dtype=np.uint8)
        img = Image.new("RGB", (self.pixel_data_width, self.pixel_data_height))
        pixels = img.load()
        if self.format_flag == b'\x08\x00\x00\x00':
            row_size = self.pixel_data_width // 2
            for y in range(self.pixel_data_height):
                for x in range(0, self.pixel_data_width, 2):
                    byte = self.pixel_data[y * row_size + (x // 2)]
                    index1 = byte & 0x0F
                    index2 = (byte >> 4) & 0x0F
                    pixels[x, y] = tuple(clut[index1])
                    if x + 1 < self.pixel_data_width:
                        pixels[x + 1, y] = tuple(clut[index2])
        elif self.format_flag == b'\x09\x00\x00\x00':
            for y in range(self.pixel_data_height):
                for x in range(self.pixel_data_width):
                    color_index = self.pixel_data[y * self.pixel_data_width + x]
                    pixels[x, y] = tuple(clut[color_index])
        pil_image = img.convert("RGBA")
        self.pil_image = pil_image
        data = pil_image.tobytes("raw", "RGBA")
        qimage = QImage(data, pil_image.width, pil_image.height, QImage.Format.Format_RGBA8888)
        return QPixmap.fromImage(qimage)
