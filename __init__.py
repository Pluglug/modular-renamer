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
        # "ui.props",  # FIXME: リロードの問題が解決しないため、Prefsにて定義
        "ui.ui",
        "targets",
        "elements.*",
        "preferences",
        # "operators.*",
    ],
    # トラブルシューティング用（順序強制指定）
    # force_order=[
    #     "utils.logging",
    #     "utils.regex_utils",
    #     "utils.screen_utils",
    #     "utils.strings_utils",
    #     "core.constants",
    #     "core.contracts.element",
    #     "core.contracts.counter",
    #     "core.contracts.namespace",
    #     "core.blender.pointer_cache",
    #     "core.target.scope",
    #     "core.contracts.target",
    #     "core.pattern.model",
    #     "core.element.registry", # elements より先に
    #     "elements.text_element",
    #     "elements.position_element",
    #     "elements.counter_element", # model より後に
    #     "core.pattern.cache",
    #     "core.pattern.factory", # props より先に factory
    #     "ui.props",           # props は factory と preferences の間
    #     "preferences",        # preferences は props の後
    #     "core.pattern.facade", # facade は factory, cache, props の後
    #     "core.namespace.manager",
    #     "core.namespace.conflict",
    #     "core.service.rename_context",
    #     "core.blender.outliner_struct",
    #     "core.blender.outliner_access",
    #     "targets",             # targets は registry の後
    #     "core.target.registry", # targets より先に
    #     "core.target.collector",
    #     "core.service.rename_service",
    #     "ui.ui",
    # ],
    use_reload=use_reload,
)


def register():
    addon.register_modules()


def unregister():
    addon.unregister_modules()
