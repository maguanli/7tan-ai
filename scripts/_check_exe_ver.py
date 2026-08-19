import zipfile, os, sys, tempfile, shutil

zip_path = r"D:\7tan\7tanAI\dist\release\7tan-editor-v1.0.13.zip"
tmp = tempfile.mkdtemp(prefix="execheck_")
try:
    with zipfile.ZipFile(zip_path) as z:
        exe_names = [n for n in z.namelist() if n.lower().endswith("7tan-editor.exe")]
        print("EXE in zip:", exe_names[:5])
        if not exe_names:
            print("NO EXE FOUND")
            sys.exit(0)
        target = exe_names[0]
        print("Extracting:", target)
        with z.open(target) as src, open(os.path.join(tmp, "7tan-editor.exe"), "wb") as dst:
            shutil.copyfileobj(src, dst)
    exe_path = os.path.join(tmp, "7tan-editor.exe")
    print("Size:", os.path.getsize(exe_path))
    # try win32api
    try:
        import win32api
        info = win32api.GetFileVersionInfo(exe_path, "\\")
        ms, ls = info['FileVersionMS'], info['FileVersionLS']
        ver = f"{ms >> 16}.{ms & 0xFFFF}.{ls >> 16}.{ls & 0xFFFF}"
        print("FileVersion:", ver)
        try:
            prod = win32api.GetFileVersionInfo(exe_path, "\\VarFileInfo\\Translation")
            for lang, codepage in prod:
                key = f"\\StringFileInfo\\{lang:04X}{codepage:04X}\\ProductVersion"
                val = win32api.GetFileVersionInfo(exe_path, key)
                print("ProductVersion:", val)
                break
        except Exception as e:
            print("ProductVersion read err:", e)
    except ImportError:
        print("win32api not available")
    # fallback: pefile
    try:
        import pefile
        pe = pefile.PE(exe_path, fast_load=True)
        pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_RESOURCE']])
        fi = pe.FileInfo
        for f in fi:
            for entry in f:
                if hasattr(entry, 'StringTable'):
                    for st in entry.StringTable:
                        for k, v in st.entries.items():
                            if b'Version' in k or b'Product' in k:
                                print(k.decode(errors='replace'), "=", v.decode(errors='replace'))
        pe.close()
    except ImportError:
        print("pefile not available")
    except Exception as e:
        print("pefile err:", e)
finally:
    shutil.rmtree(tmp, ignore_errors=True)
