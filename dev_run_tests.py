"""รันเทสต์โดยไม่ต้องมี pytest (สำหรับสภาพแวดล้อมที่ยังไม่ลง pytest).
ใช้งานจริงแนะนำ: pip install pytest แล้ว `pytest`"""
import sys, os, importlib, traceback
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "tests"))
mods = ["test_fpmath", "test_wcb"]
passed = failed = 0
for mname in mods:
    m = importlib.import_module(mname)
    for name in dir(m):
        if name.startswith("test_"):
            try:
                getattr(m, name)()
                print(f"  PASS  {mname}.{name}"); passed += 1
            except Exception:
                print(f"  FAIL  {mname}.{name}"); traceback.print_exc(); failed += 1
print(f"\nรวม {passed} PASS / {failed} FAIL")
sys.exit(1 if failed else 0)
