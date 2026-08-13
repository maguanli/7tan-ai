import sys
print("python", sys.version)
try:
    import PIL
    print("PIL", PIL.__version__)
except Exception as e:
    print("PIL missing:", e)
try:
    import numpy
    print("numpy", numpy.__version__)
except Exception as e:
    print("numpy missing:", e)
try:
    from PIL import ImageDraw, ImageFilter
    print("ImageDraw/ImageFilter OK")
except Exception as e:
    print("PIL draw missing:", e)
