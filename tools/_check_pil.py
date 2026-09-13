import sys
try:
    import PIL
    print("PIL", PIL.__version__)
except Exception as e:
    print("NO_PIL", e)
