bl_info = {
    "name": "ModularRenamer",
    "author": "Pluglug",
    "version": (0, 1, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > Tool Tab",
    "description": "A modular, customizable object naming system",
    "warning": "It'll explode.",
    "doc_url": "",
    "category": "3D View",
}

use_reload = "addon" in locals()
if use_reload:
    import importlib

    importlib.reload(locals()["addon"])
    del importlib

from . import addon

addon.init_addon(
    module_patterns=[
        "core.*",
        "utils.*",
        "ui.property_groups",
        "ui.ui",
        "targets",
        "elements.*",
        "preferences",
        # "operators.*",
    ],
    # トラブルシューティング用（順序強制指定）
    # force_order=[
    #     "addon",
    #     "utils.logging",
    #     "core",
    #     "ui",
    #     "preferences"
    # ],
    use_reload=use_reload,
)


def register():
    addon.register_modules()


def unregister():
    addon.unregister_modules()
