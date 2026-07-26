import os, shutil, sys

src = r"C:\Users\Administrator\.gradle"
dst = r"G:\gradle_cache"

os.makedirs(dst, exist_ok=True)

file_count = 0
total_size = 0
errors = 0

for dirpath, dirnames, filenames in os.walk(src):
    rel = os.path.relpath(dirpath, src)
    td = os.path.join(dst, rel)
    os.makedirs(td, exist_ok=True)
    for f in filenames:
        try:
            shutil.copy2(os.path.join(dirpath, f), os.path.join(td, f))
            file_count += 1
            total_size += os.path.getsize(os.path.join(dirpath, f))
            if file_count % 2000 == 0:
                print(f"{file_count} files, {total_size/(1024**2):.0f} MB...")
        except Exception as e:
            errors += 1
            if errors <= 3:
                print(f"ERR: {f}")

src_count = sum(1 for _ in os.walk(src) for __ in _[2])
dst_count = sum(1 for _ in os.walk(dst) for __ in _[2])
print(f"\nDone: {file_count} files, {total_size/(1024**2):.0f} MB, errors={errors}")
print(f"Src={src_count} Dst={dst_count} {'OK!' if src_count==dst_count else 'MISMATCH!'}")
