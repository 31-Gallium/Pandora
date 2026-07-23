import ctypes
import os
import sys
from PyQt6.QtGui import QImage
from utils import get_resource_path

# Globals
_engine = None
_pixel_buffer = None
_width = 0
_height = 0

def init_vis_engine(width, height, gpu_preference):
    global _engine, _width, _height
    
    _width = width
    _height = height
    
    # Define paths
    dll_name = "pandora_vis_engine.dll"
    dll_path = os.path.join(os.path.dirname(__file__), "..", dll_name)
    if not os.path.exists(dll_path):
        dll_path = get_resource_path(dll_name)
        
    if not os.path.exists(dll_path):
        print(f"[VisEngine] Could not find {dll_name}")
        return False
        
    try:
        _engine = ctypes.CDLL(dll_path)
        
        # Setup signatures
        _engine.init_visualizer.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int]
        _engine.init_visualizer.restype = ctypes.c_bool
        
        _engine.render_frame.argtypes = [
            ctypes.POINTER(ctypes.c_float), # radii
            ctypes.POINTER(ctypes.c_float), # fluids
            ctypes.c_int,                   # pts
            ctypes.c_float,                 # size
            ctypes.c_float,                 # base_thick
            ctypes.c_float,                 # gr
            ctypes.c_float,                 # gg
            ctypes.c_float,                 # gb
            ctypes.c_float,                 # hr
            ctypes.c_float,                 # hg
            ctypes.c_float,                 # hb
            ctypes.c_float                  # op_mult
        ]
        _engine.render_frame.restype = ctypes.POINTER(ctypes.c_uint8)
        
        _engine.init_mosaic.argtypes = [ctypes.POINTER(ctypes.c_uint8), ctypes.c_int, ctypes.c_int, ctypes.c_float, ctypes.c_int]
        _engine.init_mosaic.restype = None
        
        _engine.render_mosaic.argtypes = [
            ctypes.c_float, ctypes.c_float, ctypes.c_float, 
            ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_float,
            ctypes.c_float, ctypes.c_float, ctypes.c_float,
            ctypes.POINTER(ctypes.c_float), ctypes.c_float
        ]
        _engine.render_mosaic.restype = ctypes.POINTER(ctypes.c_uint8)
        
        # --- UI ENGINE ---
        _engine.init_ui_engine.argtypes = []
        _engine.init_ui_engine.restype = None

        _engine.begin_ui_frame.argtypes = [ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_float]
        _engine.begin_ui_frame.restype = None
        
        _engine.draw_d2d_ring.argtypes = [
            ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_float), ctypes.c_int, 
            ctypes.c_float, ctypes.c_float, ctypes.c_float, ctypes.c_uint32, ctypes.c_float
        ]
        _engine.draw_d2d_ring.restype = None
        
        _engine.draw_d2d_image.argtypes = [
            ctypes.POINTER(ctypes.c_uint8), ctypes.c_int, ctypes.c_int, 
            ctypes.c_float, ctypes.c_float, ctypes.c_float
        ]
        _engine.draw_d2d_image.restype = None
        
        _engine.end_ui_frame.argtypes = []
        _engine.end_ui_frame.restype = ctypes.POINTER(ctypes.c_uint8)
        
        _engine.destroy_visualizer.argtypes = []
        _engine.destroy_visualizer.restype = None
        
        _engine.get_bound_gpu_name.argtypes = []
        _engine.get_bound_gpu_name.restype = ctypes.c_char_p
        
        success = _engine.init_visualizer(width, height, gpu_preference)
        print(f"[VisEngine] Initialization {'successful' if success else 'failed'}")
        return success
    except Exception as e:
        print(f"[VisEngine] Failed to load DLL: {e}")
        return False

def render_vis_frame(radii, fluids, size, base_thick, gr, gg, gb, hr, hg, hb, op_mult):
    global _engine, _pixel_buffer, _width, _height
    if _engine is None:
        return None
        
    pts = len(radii) - 1
    
    # Convert lists to ctypes arrays
    float_array = ctypes.c_float * len(radii)
    c_radii = float_array(*radii)
    c_fluids = float_array(*fluids)
    
    buf_ptr = _engine.render_frame(c_radii, c_fluids, pts, size, base_thick, gr, gg, gb, hr, hg, hb, op_mult)
    
    if not buf_ptr:
        return None
        
    buf_size = _width * _height * 4
    
    global _bytearray_buffer
    if '_bytearray_buffer' not in globals() or _bytearray_buffer is None:
        _bytearray_buffer = bytearray(buf_size)
        
    raw_addr = ctypes.cast(buf_ptr, ctypes.c_void_p).value
    c_char_array = (ctypes.c_char * buf_size).from_buffer(_bytearray_buffer)
    ctypes.memmove(ctypes.addressof(c_char_array), raw_addr, buf_size)
    
    qimg = QImage(_bytearray_buffer, _width, _height, QImage.Format.Format_ARGB32_Premultiplied)
    
    _pixel_buffer = _bytearray_buffer
    return qimg

def init_ui_engine():
    if _engine: _engine.init_ui_engine()

def begin_ui_frame(r=0.0, g=0.0, b=0.0, a=0.0):
    if _engine: _engine.begin_ui_frame(r, g, b, a)

def draw_d2d_ring(radii, fluids, size, base_thick, color, opacity):
    if not _engine: return
    pts = len(radii) - 1
    float_array = ctypes.c_float * len(radii)
    c_radii = float_array(*radii)
    c_fluids = float_array(*fluids)
    _engine.draw_d2d_ring(c_radii, c_fluids, pts, _width/2.0, _height/2.0, base_thick, color, opacity)

def draw_d2d_image(qimage, cx, cy, scale=1.0):
    if not _engine: return
    if qimage.format() != QImage.Format.Format_ARGB32_Premultiplied:
        qimage = qimage.convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)
    
    w, h = qimage.width(), qimage.height()
    ptr = qimage.constBits()
    ptr.setsize(w * h * 4)
    img_data = ctypes.cast(ptr.asstring(), ctypes.POINTER(ctypes.c_uint8))
    
    _engine.draw_d2d_image(img_data, w, h, cx, cy, scale)

def end_ui_frame():
    global _engine, _pixel_buffer, _width, _height
    if not _engine: return None
    
    buf_ptr = _engine.end_ui_frame()
    if not buf_ptr: return None
    
    buf_size = _width * _height * 4
    global _bytearray_buffer
    if '_bytearray_buffer' not in globals() or _bytearray_buffer is None:
        _bytearray_buffer = bytearray(buf_size)
        
    raw_addr = ctypes.cast(buf_ptr, ctypes.c_void_p).value
    c_char_array = (ctypes.c_char * buf_size).from_buffer(_bytearray_buffer)
    ctypes.memmove(ctypes.addressof(c_char_array), raw_addr, buf_size)
    
    qimg = QImage(_bytearray_buffer, _width, _height, QImage.Format.Format_ARGB32_Premultiplied)
    return qimg

def init_mosaic(qimage, block_size, shape_str):
    global _engine
    if _engine is None or qimage is None: return
    
    shape = 1 if shape_str == "Rounded" else 0
    
    img = qimage.convertToFormat(QImage.Format.Format_ARGB32)
    ptr = img.bits()
    ptr.setsize(img.sizeInBytes())
    
    c_array = (ctypes.c_uint8 * img.sizeInBytes()).from_buffer_copy(ptr)
    _engine.init_mosaic(c_array, img.width(), img.height(), ctypes.c_float(block_size), ctypes.c_int(shape))

def render_mosaic(bass_e, mids_e, treble_e, ext_factor, w_x, w_y, d_x, d_y, bass_phase, mids_phase, treble_phase, ring_thick_list, global_op):
    global _engine, _width, _height
    if _engine is None: return None
    
    float_array = ctypes.c_float * 8
    c_ring_thick = float_array(*ring_thick_list)
    
    buf_ptr = _engine.render_mosaic(
        ctypes.c_float(bass_e), ctypes.c_float(mids_e), ctypes.c_float(treble_e),
        ctypes.c_float(ext_factor), ctypes.c_float(w_x), ctypes.c_float(w_y), ctypes.c_float(d_x), ctypes.c_float(d_y),
        ctypes.c_float(bass_phase), ctypes.c_float(mids_phase), ctypes.c_float(treble_phase),
        c_ring_thick, ctypes.c_float(global_op)
    )
    if not buf_ptr: return None
    
    buf_size = 512 * 512 * 4
    global _particle_bytearray
    if '_particle_bytearray' not in globals() or _particle_bytearray is None:
        _particle_bytearray = bytearray(buf_size)
        
    raw_addr = ctypes.cast(buf_ptr, ctypes.c_void_p).value
    c_char_array = (ctypes.c_char * buf_size).from_buffer(_particle_bytearray)
    ctypes.memmove(ctypes.addressof(c_char_array), raw_addr, buf_size)
    
    qimg = QImage(_particle_bytearray, 512, 512, QImage.Format.Format_ARGB32_Premultiplied)
    global _particle_ref
    _particle_ref = _particle_bytearray
    return qimg


def init_ferrofluid(qimage):
    global _engine
    if _engine is None or qimage is None: return
    
    img = qimage.convertToFormat(QImage.Format.Format_ARGB32)
    ptr = img.bits()
    ptr.setsize(img.sizeInBytes())
    
    c_array = (ctypes.c_uint8 * img.sizeInBytes()).from_buffer_copy(ptr)
    _engine.init_ferrofluid(c_array, img.width(), img.height())

def render_ferrofluid(bass_e, mids_e, treble_e, time_t, use_texture, dominant_color, global_op):
    global _engine
    if _engine is None: return None
    
    buf_ptr = _engine.render_ferrofluid(
        ctypes.c_float(bass_e), ctypes.c_float(mids_e), ctypes.c_float(treble_e),
        ctypes.c_float(time_t), ctypes.c_int(use_texture), ctypes.c_uint32(dominant_color), ctypes.c_float(global_op)
    )
    if not buf_ptr: return None
    
    buf_size = 512 * 512 * 4
    global _particle_bytearray
    if '_particle_bytearray' not in globals() or _particle_bytearray is None:
        _particle_bytearray = bytearray(buf_size)
        
    raw_addr = ctypes.cast(buf_ptr, ctypes.c_void_p).value
    c_char_array = (ctypes.c_char * buf_size).from_buffer(_particle_bytearray)
    ctypes.memmove(ctypes.addressof(c_char_array), raw_addr, buf_size)
    
    qimg = QImage(_particle_bytearray, 512, 512, QImage.Format.Format_ARGB32_Premultiplied)
    global _particle_ref
    _particle_ref = _particle_bytearray
    return qimg

def destroy_vis_engine():

    global _engine
    if _engine is not None:
        _engine.destroy_visualizer()
        
    # On Windows, you can't easily unload a CDLL using ctypes without relying on kernel32.FreeLibrary
    # but we can try to release the reference.
    if sys.platform == 'win32':
        import _ctypes
        _ctypes.FreeLibrary(_engine._handle)
    _engine = None

def get_bound_gpu_name():
    global _engine
    if not _engine: return "None"
    try:
        val = _engine.get_bound_gpu_name()
        if val:
            return val.decode('utf-8', errors='ignore')
    except Exception:
        pass
    return "Unknown"
