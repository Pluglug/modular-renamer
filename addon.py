"""
Blenderアドオン開発用の拡張可能なフレームワーク

特徴:
- モジュールの依存関係自動解決
- 循環依存検出機能
- 柔軟なモジュールパターン指定
- 詳細なデバッグ出力
- クラス自動登録システム
"""

import bpy
import importlib
import os
import pkgutil
import sys
import inspect
import re
from collections import defaultdict
from typing import List, Dict, Set, Pattern

# from .utils.logging import get_logger

# log = get_logger(__name__)

# ======================================================
# グローバル設定
# ======================================================

DBG_INIT = True
BACKGROUND = False
VERSION = (0, 0, 0)  # アドオンバージョン
BL_VERSION = (0, 0, 0)  # 対応Blenderバージョン

# アドオン基本情報
ADDON_PATH = os.path.dirname(os.path.abspath(__file__))
ADDON_ID = os.path.basename(ADDON_PATH)
TEMP_PREFS_ID = f"addon_{ADDON_ID}"
ADDON_PREFIX = "".join([s[0] for s in re.split(r"[_-]", ADDON_ID)]).upper()
ADDON_PREFIX_PY = ADDON_PREFIX.lower()

# モジュール管理用
MODULE_NAMES: List[str] = []
MODULE_PATTERNS: List[Pattern] = []
ICON_ENUM_ITEMS = (
    bpy.types.UILayout.bl_rna.functions["prop"].parameters["icon"].enum_items
)

# キャッシュ
_class_cache: List[bpy.types.bpy_struct] = None

# ======================================================
# ユーティリティ関数
# ======================================================


def uprefs(context: bpy.types.Context = bpy.context) -> bpy.types.Preferences:
    """ユーザープリファレンスを取得"""
    preferences = getattr(context, "preferences", None)
    if preferences is not None:
        return preferences
    raise AttributeError("プリファレンスにアクセスできません")


def prefs(context: bpy.types.Context = bpy.context) -> bpy.types.AddonPreferences:
    """アドオン設定を取得"""
    user_prefs = uprefs(context)
    addon_prefs = user_prefs.addons.get(ADDON_ID)
    if addon_prefs is not None:
        return addon_prefs.preferences
    raise KeyError(f"アドオン'{ADDON_ID}'が見つかりません")


def temp_prefs() -> bpy.types.PropertyGroup:
    """一時設定を取得"""
    return getattr(bpy.context.window_manager, TEMP_PREFS_ID, None)


# ======================================================
# モジュール管理コア
# ======================================================


def init_addon(
    module_patterns: List[str],
    use_reload: bool = False,
    background: bool = False,
    prefix: str = None,
    prefix_py: str = None,
) -> None:
    """
    アドオンを初期化

    Args:
        module_patterns (List[str]): ロードするモジュールのパターンリスト
        use_reload (bool): リロードを使用するか
        background (bool): バックグラウンドモード
        prefix (str): オペレータ接頭辞
        prefix_py (str): Python用接頭辞

    Example:
        init_addon(
            module_patterns=[
                "core",
                "utils.*",
                "operators.*_ops",
                "ui.panels"
            ],
            use_reload=True
        )
    """
    global VERSION, BL_VERSION, ADDON_PREFIX, ADDON_PREFIX_PY, _class_cache

    # 初期化処理
    _class_cache = None
    module = sys.modules[ADDON_ID]
    VERSION = module.bl_info.get("version", VERSION)
    BL_VERSION = module.bl_info.get("blender", BL_VERSION)

    if prefix:
        ADDON_PREFIX = prefix
    if prefix_py:
        ADDON_PREFIX_PY = prefix_py

    # パターンコンパイル
    MODULE_PATTERNS[:] = [
        re.compile(f"^{ADDON_ID}\.{p.replace('*', '.*')}$") for p in module_patterns
    ]

    # モジュール収集
    module_names = list(_collect_module_names())

    # モジュール事前ロード
    for module_name in module_names:
        if use_reload and module_name in sys.modules:
            importlib.reload(sys.modules[module_name])
        else:
            importlib.import_module(module_name)

    # 依存関係解決
    # sorted_modules = _sort_modules(module_names)
    # MODULE_NAMES[:] = sorted_modules

    # 上手くいかないので強制的に登録
    MODULE_NAMES[:] = [
        "modular-renamer.addon",
        "modular-renamer.utils.logging",
        "modular-renamer.core",
        "modular-renamer.ui",
        "modular-renamer.preferences",
    ]

    if DBG_INIT:
        print("\n=== 最終モジュールロード順序 ===")
        for mod in MODULE_NAMES:
            print(f" - {mod}")


# ======================================================
# 依存関係解析
# ======================================================


def _analyze_dependencies(module_names: List[str]) -> Dict[str, Set[str]]:
    """
    モジュール間の依存関係を解析

    Returns:
        Dict[str, Set[str]]: 依存関係グラフ
    """
    graph = defaultdict(set)
    pdtype = bpy.props._PropertyDeferred

    for mod_name in module_names:
        mod = sys.modules.get(mod_name)
        if not mod:
            continue

        # クラス依存関係解析
        for _, cls in inspect.getmembers(mod, _is_bpy_class):
            for prop in getattr(cls, "__annotations__", {}).values():
                if isinstance(prop, pdtype) and prop.function in [
                    bpy.props.PointerProperty,
                    bpy.props.CollectionProperty,
                ]:
                    dep_cls = prop.keywords.get("type")
                    if not dep_cls:
                        continue
                    dep_mod = dep_cls.__module__
                    # 同一モジュールなら依存関係扱いしない (誤検知防止)
                    if dep_mod == mod_name:
                        continue

                    # ここを逆にする:
                    if dep_mod in module_names:
                        # graph[dep_mod].add(mod_name)
                        graph[mod_name].add(dep_mod)

        # 明示的依存関係
        if hasattr(mod, "DEPENDS_ON"):
            for dep in mod.DEPENDS_ON:
                dep_full = f"{ADDON_ID}.{dep}"
                if dep_full in module_names:
                    # ここも逆に:
                    # graph[dep_full].add(mod_name)
                    graph[mod_name].add(dep_full)

    return graph


def _sort_modules(module_names: List[str]) -> List[str]:
    """
    モジュールを依存関係順にソート

    Returns:
        List[str]: ソート済みモジュールリスト
    """
    graph = _analyze_dependencies(module_names)
    valid_nodes = [n for n in graph if n in module_names]
    filtered_graph = {
        n: [d for d in deps if d in module_names]
        for n, deps in graph.items()
        if n in module_names
    }

    if DBG_INIT:
        print("\n=== 依存関係グラフ ===")
        for mod, deps in graph.items():
            print(f"{mod} depends on:")
            for d in deps:
                print(f"  → {d}")

    try:
        sorted_modules = _topological_sort(filtered_graph)
    except ValueError as e:
        print(f"警告: {str(e)}")
        sorted_modules = module_names

    # 未処理モジュールを末尾に追加
    remaining = [m for m in module_names if m not in sorted_modules]
    return sorted_modules + remaining


def _topological_sort(graph: Dict[str, List[str]]) -> List[str]:
    """
    Kahnのアルゴリズムによるトポロジカルソート

    Args:
        graph (Dict[str, List[str]]): 依存関係グラフ

    Returns:
        List[str]: ソート済みリスト

    Raises:
        ValueError: 循環依存検出時
    """
    in_degree = defaultdict(int)
    for node in graph:
        for neighbor in graph[node]:
            in_degree[neighbor] += 1

    queue = [node for node in graph if in_degree[node] == 0]
    sorted_order = []

    while queue:
        node = queue.pop(0)
        sorted_order.append(node)
        for neighbor in graph.get(node, []):
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    if len(sorted_order) != len(graph):
        cyclic = set(graph.keys()) - set(sorted_order)
        raise ValueError(f"循環依存検出: {', '.join(cyclic)}")

    return sorted_order


# ======================================================
# モジュール登録/登録解除
# ======================================================


def register_modules() -> None:
    """全モジュールを登録"""
    if BACKGROUND and bpy.app.background:
        return

    classes = _get_classes()
    success = True

    # クラス登録
    for cls in classes:
        try:
            _validate_class(cls)
            bpy.utils.register_class(cls)
            if DBG_INIT:
                print(f"✓ 登録完了: {cls.__name__}")
        except Exception as e:
            success = False
            print(f"✗ クラス登録失敗: {cls.__name__}")
            print(f"   理由: {str(e)}")
            print(f"   モジュール: {cls.__module__}")
            if hasattr(cls, "__annotations__"):
                print(f"   アノテーション: {list(cls.__annotations__.keys())}")

    # モジュール初期化
    for mod_name in MODULE_NAMES:
        try:
            mod = sys.modules[mod_name]
            if hasattr(mod, "register"):
                mod.register()
                if DBG_INIT:
                    print(f"✓ 初期化完了: {mod_name}")
        except Exception as e:
            success = False
            print(f"✗ モジュール初期化失敗: {mod_name}")
            print(f"   理由: {str(e)}")
            import traceback

            traceback.print_exc()

    if not success:
        print("警告: 一部コンポーネントの初期化に失敗しました")


def unregister_modules() -> None:
    """全モジュールを登録解除"""
    if BACKGROUND and bpy.app.background:
        return

    # モジュール逆初期化
    for mod_name in reversed(MODULE_NAMES):
        try:
            mod = sys.modules[mod_name]
            if hasattr(mod, "unregister"):
                mod.unregister()
        except Exception as e:
            print(f"モジュール登録解除エラー: {mod_name} - {str(e)}")

    # クラス登録解除
    for cls in reversed(_get_classes()):
        try:
            bpy.utils.unregister_class(cls)
        except Exception as e:
            print(f"クラス登録解除エラー: {cls.__name__} - {str(e)}")


# ======================================================
# ヘルパー関数
# ======================================================


def _collect_module_names() -> List[str]:
    """パターンに一致するモジュール名を収集"""

    def is_masked(name: str) -> bool:
        return any(p.match(name) for p in MODULE_PATTERNS)

    def scan(path: str, package: str) -> List[str]:
        modules = []
        for _, name, is_pkg in pkgutil.iter_modules([path]):
            if name.startswith("_"):
                continue

            full_name = f"{package}.{name}"
            if is_pkg:
                modules.extend(scan(os.path.join(path, name), full_name))
            if is_masked(full_name):
                modules.append(full_name)
        return modules

    return scan(ADDON_PATH, ADDON_ID)


def _get_classes(force: bool = True) -> List[bpy.types.bpy_struct]:
    """登録対象クラスを取得"""
    global _class_cache
    if not force and _class_cache:
        return _class_cache

    class_deps = defaultdict(set)
    pdtype = getattr(bpy.props, "_PropertyDeferred", tuple)

    # クラス収集
    all_classes = []
    for mod_name in MODULE_NAMES:
        mod = sys.modules[mod_name]
        for _, cls in inspect.getmembers(mod, _is_bpy_class):
            deps = set()
            for prop in getattr(cls, "__annotations__", {}).values():
                if isinstance(prop, pdtype):
                    pfunc = getattr(prop, "function", None) or prop[0]
                    if pfunc in (
                        bpy.props.PointerProperty,
                        bpy.props.CollectionProperty,
                    ):
                        if dep_cls := prop.keywords.get("type"):
                            if dep_cls.__module__.startswith(ADDON_ID):
                                deps.add(dep_cls)
            class_deps[cls] = deps
            all_classes.append(cls)

    # 依存関係ソート
    ordered = []
    visited = set()
    stack = []

    def visit(cls):
        if cls in stack:
            cycle = " → ".join([c.__name__ for c in stack])
            raise ValueError(f"クラス循環依存: {cycle}")
        if cls not in visited:
            stack.append(cls)
            visited.add(cls)
            for dep in class_deps.get(cls, []):
                visit(dep)
            stack.pop()
            ordered.append(cls)

    for cls in all_classes:
        if cls not in visited:
            visit(cls)

    if DBG_INIT:
        print("\n=== 登録クラス一覧 ===")
        for cls in ordered:
            print(f" - {cls.__name__}")

    _class_cache = ordered
    return ordered


def _is_bpy_class(obj) -> bool:
    """bpy構造体クラスか判定"""
    return (
        inspect.isclass(obj)
        and issubclass(obj, bpy.types.bpy_struct)
        and obj.__base__ is not bpy.types.bpy_struct
    )


def _validate_class(cls: bpy.types.bpy_struct) -> None:
    """クラスの有効性を検証"""
    if not hasattr(cls, "bl_rna"):
        raise ValueError(f"クラス {cls.__name__} にbl_rna属性がありません")
    if not issubclass(cls, bpy.types.bpy_struct):
        raise TypeError(f"無効なクラス型: {cls.__name__}")


# ======================================================
# タイムアウト管理
# ======================================================


class Timeout(bpy.types.Operator):
    """遅延実行用オペレータ"""

    bl_idname = f"{ADDON_PREFIX_PY}.timeout"
    bl_label = ""
    bl_options = {"INTERNAL"}

    idx: bpy.props.IntProperty(options={"SKIP_SAVE", "HIDDEN"})
    delay: bpy.props.FloatProperty(default=0.0001, options={"SKIP_SAVE", "HIDDEN"})

    _data: Dict[int, tuple] = dict()
    _timer = None
    _finished = False

    def modal(self, context, event):
        if event.type == "TIMER":
            if self._finished:
                context.window_manager.event_timer_remove(self._timer)
                del self._data[self.idx]
                return {"FINISHED"}

            if self._timer.time_duration >= self.delay:
                self._finished = True
                try:
                    func, args = self._data[self.idx]
                    func(*args)
                except Exception as e:
                    print(f"タイムアウトエラー: {str(e)}")
        return {"PASS_THROUGH"}

    def execute(self, context):
        self._finished = False
        context.window_manager.modal_handler_add(self)
        self._timer = context.window_manager.event_timer_add(
            self.delay, window=context.window
        )
        return {"RUNNING_MODAL"}


def timeout(func: callable, *args) -> None:
    """関数を遅延実行"""
    idx = len(Timeout._data)
    while idx in Timeout._data:
        idx += 1
    Timeout._data[idx] = (func, args)
    getattr(bpy.ops, ADDON_PREFIX_PY).timeout(idx=idx)


# ======================================================
# モジュールパターン指定ガイド
# ======================================================
"""
モジュールパターン指定方法:

init_addon()のmodule_patterns引数で使用可能なパターン形式:

1. 完全一致: "utils.helpers"
   - utilsパッケージ内のhelpersモジュールのみ

2. ワイルドカード: "operators.*"
   - operatorsパッケージ内の全モジュール
   - 例: operators.transform, operators.edit など

3. 部分一致: "ui.*_panel"
   - uiパッケージ内で末尾が_panelのモジュール
   - 例: ui.tool_panel, ui.side_panel

4. 複合パターン:
   [
     "core",
     "utils.*",
     "operators.*_op",
     "ui.*_panel"
   ]

注意点:
- パッケージ指定時は配下の全モジュールを自動的に含みません
- 明示的な指定が必要です
- 依存関係は自動的に解決されます
- 優先順位: リストの前方にあるパターンが優先

推奨構造:
addon/
├── core/           # コア機能
├── operators/      # オペレータ
├── ui/             # UI関連
├── utils/          # ユーティリティ
└── preferences.py  # 設定
"""
