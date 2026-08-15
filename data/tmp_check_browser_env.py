import importlib
for m in ["playwright", "selenium", "requests", "websocket", "aiohttp"]:
    try:
        mod = importlib.import_module(m)
        print(m, "OK", getattr(mod, "__version__", ""))
    except Exception as e:
        print(m, "MISSING", type(e).__name__)
