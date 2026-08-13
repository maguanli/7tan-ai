import os, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
root = r'C:\Users\Administrator\.cache\huggingface\hub'
found = []
for dirpath, dirnames, filenames in os.walk(root):
    for fn in filenames:
        if fn.endswith(('.onnx', '.zip', '.pth')):
            full = os.path.join(dirpath, fn)
            try:
                size = os.path.getsize(full)
            except Exception:
                size = -1
            found.append((full, size))
for f, s in found:
    print(f'{s:>12}  {f}')
print('TOTAL', len(found))
