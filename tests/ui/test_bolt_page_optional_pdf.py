import builtins
import importlib
import os
import sys


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def test_bolt_page_import_succeeds_without_reportlab(monkeypatch) -> None:
    removed_modules = {}
    for module_name in list(sys.modules):
        if module_name == "app.ui.pages.bolt_page" or module_name == "app.ui.report_pdf" or module_name.startswith("reportlab"):
            removed_modules[module_name] = sys.modules.pop(module_name)

    original_import = builtins.__import__

    def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name.startswith("reportlab"):
            raise ModuleNotFoundError("No module named 'reportlab'")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", guarded_import)

    try:
        module = importlib.import_module("app.ui.pages.bolt_page")
        assert hasattr(module, "BoltPage")
    finally:
        sys.modules.pop("app.ui.pages.bolt_page", None)
        sys.modules.pop("app.ui.report_pdf", None)
        for module_name, module in removed_modules.items():
            sys.modules[module_name] = module
