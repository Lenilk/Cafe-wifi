#!/usr/bin/env python3
"""
mini test runner สำหรับใช้คู่กับ /tmp/stubs/pytest shim ในแซนด์บ็อกซ์นี้เท่านั้น
ใช้งาน:  PYTHONPATH=/tmp/stubs:app python3 tests/_run_tests.py tests/test_x.py [test_y.py ...]

บนเครื่องจริงที่มีอินเทอร์เน็ต ให้ใช้ pytest ตัวจริงแทน (pip install pytest && pytest tests/ -v)
ไฟล์นี้ไม่ใช่ส่วนหนึ่งของการส่งมอบ — เป็นเครื่องมือช่วยยืนยันผลในสภาพแวดล้อมพัฒนาเท่านั้น
"""
from __future__ import annotations

import importlib
import importlib.util
import inspect
import pathlib
import sys
import tempfile
import traceback

import pytest as _pytest_shim  # ต้องมาจาก /tmp/stubs ที่ใส่ใน PYTHONPATH ก่อน app/

ROOT = pathlib.Path(__file__).resolve().parent


def _collect_fixtures(module) -> dict:
    fx = {}
    for name, obj in vars(module).items():
        if callable(obj) and getattr(obj, "_is_fixture", False):
            fx[name] = obj
    return fx


def _resolve(name, fixtures, cache, extra):
    if name == "monkeypatch":
        if "monkeypatch" not in cache:
            mp = _pytest_shim.MonkeyPatch()
            cache["monkeypatch"] = mp
            extra.setdefault("_teardown", []).append(mp.undo)
        return cache["monkeypatch"]
    if name == "tmp_path":
        if "tmp_path" not in cache:
            cache["tmp_path"] = pathlib.Path(tempfile.mkdtemp())
        return cache["tmp_path"]
    if name in cache:
        return cache[name]
    if name not in fixtures:
        raise LookupError(f"ไม่พบ fixture ชื่อ '{name}'")
    func = fixtures[name]
    params = list(inspect.signature(func).parameters)
    kwargs = {p: _resolve(p, fixtures, cache, extra) for p in params}
    if inspect.isgeneratorfunction(func):
        gen = func(**kwargs)
        value = next(gen)
        extra.setdefault("_teardown", []).append(lambda g=gen: next(g, None))
    else:
        value = func(**kwargs)
    cache[name] = value
    return value


def run_module(path: pathlib.Path, results: list):
    conftest_path = path.parent / "conftest.py"
    fixtures = {}
    if conftest_path.exists():
        spec = importlib.util.spec_from_file_location("conftest", conftest_path)
        conftest = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(conftest)
        fixtures.update(_collect_fixtures(conftest))

    modname = path.stem
    spec = importlib.util.spec_from_file_location(modname, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[modname] = mod
    spec.loader.exec_module(mod)
    fixtures.update(_collect_fixtures(mod))

    test_funcs = [(n, o) for n, o in vars(mod).items()
                  if n.startswith("test_") and callable(o) and not getattr(o, "_is_fixture", False)]

    for name, func in test_funcs:
        param_spec = getattr(func, "_pytest_parametrize", None)
        cases = [{}]
        if param_spec:
            argnames, argvalues = param_spec
            names = [a.strip() for a in argnames.split(",")]
            cases = []
            for vals in argvalues:
                if not isinstance(vals, (tuple, list)):
                    vals = (vals,)
                cases.append(dict(zip(names, vals)))

        for i, case_kwargs in enumerate(cases):
            label = name if len(cases) == 1 else f"{name}[{i}]"
            extra = {}
            cache = dict(case_kwargs)
            sig_params = [p for p in inspect.signature(func).parameters if p not in case_kwargs]
            try:
                kwargs = dict(case_kwargs)
                for p in sig_params:
                    kwargs[p] = _resolve(p, fixtures, cache, extra)
                func(**kwargs)
                results.append((f"{path.name}::{label}", True, ""))
            except Exception as exc:  # noqa: BLE001
                tb = traceback.format_exc()
                results.append((f"{path.name}::{label}", False, f"{exc}\n{tb}"))
            finally:
                for td in extra.get("_teardown", []):
                    try:
                        td()
                    except Exception:
                        pass


def main(argv):
    files = [pathlib.Path(a) for a in argv] or sorted(ROOT.glob("test_*.py"))
    results: list = []
    for f in files:
        run_module(f, results)

    passed = [r for r in results if r[1]]
    failed = [r for r in results if not r[1]]
    for name, ok, msg in results:
        print(("  PASS  " if ok else "  FAIL  ") + name)
        if not ok:
            print("         " + msg.replace("\n", "\n         "))
    print()
    print(f"=== {len(passed)} ผ่าน, {len(failed)} ล้มเหลว จากทั้งหมด {len(results)} ===")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
