import importlib


def test_imports():
    modules = [
        "zkbot_controller.app",
        "zkbot_controller.gui",
        "zkbot_controller.serial_comm",
        "zkbot_controller.models",
    ]
    for m in modules:
        importlib.import_module(m)
