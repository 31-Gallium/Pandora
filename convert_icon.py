from PIL import Image

try:
    img = Image.open('icon.ico')
    img.save('icon_valid.ico', format='ICO', sizes=[(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)])
    print("Successfully converted icon.")
except Exception as e:
    print(f"Error: {e}")
