import sys
import os
import ctypes
from PyQt6.QtGui import QImage, QPainter, QPixmap
from PyQt6.QtWidgets import QApplication
import time

app = QApplication([])

buf_size = 512 * 512 * 4
_bytearray_buffer = bytearray(buf_size)

# simulate getting a pointer from C++
raw_data = (ctypes.c_uint8 * buf_size)()
for i in range(100): raw_data[i] = 255 # put some data
raw_addr = ctypes.addressof(raw_data)

# Copy into bytearray
c_char_array = (ctypes.c_char * buf_size).from_buffer(_bytearray_buffer)
ctypes.memmove(ctypes.addressof(c_char_array), raw_addr, buf_size)

qimg = QImage(_bytearray_buffer, 512, 512, QImage.Format.Format_ARGB32_Premultiplied)

pix = QPixmap(512, 512)
p = QPainter(pix)
p.drawImage(0, 0, qimg)
p.end()

print("Drawn successfully, isNull:", qimg.isNull())
