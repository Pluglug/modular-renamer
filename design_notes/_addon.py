# """
# Blenderアドオン開発用の拡張可能なフレームワーク

# 特徴:
# - モジュールの依存関係自動解決
# - 循環依存検出機能
# - 柔軟なモジュールパターン指定
# - 詳細なデバッグ出力
# - クラス自動登録システム
# """

# import importlib
# import inspect
# import os
# import pkgutil
# import re
# import sys
# from collections import defaultdict
# from typing import Dict, List, Pattern, Set

# import bpy

# # from .utils.logging import get_logger
# # log = get_logger(__name__)

# # ======================================================
# # グローバル設定
# # ======================================================

# DBG_INIT = True  # 初期化時のデバッグ出力
# CREATE_DEPENDENCY_GRAPH = True  # 依存関係グラフの作成
# BACKGROUND = False  # バックグラウンドモードの有効化
# VERSION = (0, 0, 0)  # アドオンバージョン
# BL_VERSION = (0, 0, 0)  # 対応Blenderバージョン

# # アドオン基本情報
# ADDON_PATH = os.path.dirname(os.path.abspath(__file__))
# ADDON_ID = os.path.basename(ADDON_PATH)
# TEMP_PREFS_ID = f"addon_{ADDON_ID}"
# ADDON_PREFIX = "".join([s[0] for s in re.split(r"[_-]", ADDON_ID)]).upper()
# ADDON_PREFIX_PY = ADDON_PREFIX.lower()

# # モジュール管理用
# MODULE_NAMES: List[str] = []  # ロード順序が解決されたモジュールリスト
# MODULE_PATTERNS: List[Pattern] = []  # 読み込み対象のモジュールパターン
# ICON_ENUM_ITEMS = (
#     bpy.types.UILayout.bl_rna.functions["prop"].parameters["icon"].enum_items
# )

# # キャッシュ
# _class_cache: List[bpy.types.bpy_struct] = None

# # ======================================================
# # ユーティリティ関数
# # ======================================================

# def short_name(module_name: str) -> str:
#     """
#     モジュール名を短縮形で返す（アドオンIDを除去）

#     Args:
#         module_name: 完全なモジュール名

#     Returns:
#         str: アドオンIDを除いた短縮名
#     """
#     prefix = f"{ADDON_ID}."
#     return module_name[len(prefix) :] if module_name.startswith(prefix) else module_name

# def uprefs(context: bpy.types.Context = bpy.context) -> bpy.types.Preferences:
#     """
#     ユーザープリファレンスを取得

#     Args:
#         context: Blenderコンテキスト（デフォルトはbpy.context）

#     Returns:
#         bpy.types.Preferences: ユーザー設定

#     Raises:
#         AttributeError: プリファレンスにアクセスできない場合
#     """
#     preferences = getattr(context, "preferences", None)
#     if preferences is not None:
#         return preferences
#     raise AttributeError("プリファレンスにアクセスできません")


# def prefs(context: bpy.types.Context = bpy.context) -> "ModularRenamerPreferences":
#     """
#     アドオン設定を取得

#     Args:
#         context: Blenderコンテキスト（デフォルトはbpy.context）

#     Returns:
#         bpy.types.AddonPreferences: アドオン設定

#     Raises:
#         KeyError: アドオンが見つからない場合
#     """
#     user_prefs = uprefs(context)
#     addon_prefs = user_prefs.addons.get(ADDON_ID)
#     if addon_prefs is not None:
#         return addon_prefs.preferences
#     raise KeyError(f"アドオン'{ADDON_ID}'が見つかりません")


# def temp_prefs() -> bpy.types.PropertyGroup:
#     """
#     一時設定を取得

#     Returns:
#         bpy.types.PropertyGroup: 一時的な設定オブジェクト
#     """
#     return getattr(bpy.context.window_manager, TEMP_PREFS_ID, None)


# # ======================================================
# # モジュール管理コア
# # ======================================================


# def init_addon(
#     module_patterns: List[str],
#     use_reload: bool = False,
#     background: bool = False,
#     prefix: str = None,
#     prefix_py: str = None,
#     force_order: List[str] = None,  # トラブルシューティング用
# ) -> None:
#     """
#     アドオンを初期化

#     この関数は次の順序で処理を行います:
#     1. モジュールパターンに基づいてロード対象モジュールを収集
#     2. 各モジュールをロード（必要に応じてリロード）
#     3. モジュール間の依存関係を解析
#     4. トポロジカルソートによるロード順序の決定
#     5. モジュールリストの保存とデバッグ情報の出力

#     Args:
#         module_patterns (List[str]): ロードするモジュールのパターンリスト
#         use_reload (bool): リロードを使用するか
#         background (bool): バックグラウンドモード
#         prefix (str): オペレータ接頭辞
#         prefix_py (str): Python用接頭辞
#         force_order (List[str]): 強制的なモジュールロード順序（トラブルシューティング用）

#     Example:
#         init_addon(
#             module_patterns=[
#                 "core",
#                 "utils.*",
#                 "operators.*_ops",
#                 "ui.panels"
#             ],
#             use_reload=True
#         )
#     """
#     global VERSION, BL_VERSION, ADDON_PREFIX, ADDON_PREFIX_PY, _class_cache

#     # 初期化処理
#     _class_cache = None
#     module = sys.modules[ADDON_ID]
#     VERSION = module.bl_info.get("version", VERSION)
#     BL_VERSION = module.bl_info.get("blender", BL_VERSION)

#     if prefix:
#         ADDON_PREFIX = prefix
#     if prefix_py:
#         ADDON_PREFIX_PY = prefix_py

#     # パターンコンパイル
#     MODULE_PATTERNS[:] = [
#         re.compile(f"^{ADDON_ID}\.{p.replace('*', '.*')}$") for p in module_patterns
#     ]

#     # アドオンモジュール自体も追加
#     MODULE_PATTERNS.append(re.compile(f"^{ADDON_ID}$"))

#     # モジュール収集
#     module_names = list(_collect_module_names())

#     # モジュール事前ロード
#     for module_name in module_names:
#         try:
#             if use_reload and module_name in sys.modules:
#                 importlib.reload(sys.modules[module_name])
#             else:
#                 importlib.import_module(module_name)
#         except Exception as e:
#             print(f"モジュール {module_name} のロードに失敗: {str(e)}")

#     # 依存関係解決
#     if force_order:
#         # ------------------------------------------------------
#         # トラブルシューティング用: 強制的なモジュールロード順序
#         # ------------------------------------------------------
#         print("\n=== 強制指定されたモジュールロード順序を使用 ===")
#         sorted_modules = _resolve_forced_order(force_order, module_names)
#     else:
#         # ------------------------------------------------------
#         # 通常の依存関係解析による自動順序決定
#         # ------------------------------------------------------
#         sorted_modules = _sort_modules(module_names)

#     MODULE_NAMES[:] = sorted_modules

#     if DBG_INIT:
#         print("\n=== 最終モジュールロード順序 ===")
#         for i, mod in enumerate(MODULE_NAMES, 1):
#             short = short_name(mod)
#             print(f"{i:2d}. {short}")


# def _resolve_forced_order(force_order: List[str], module_names: List[str]) -> List[str]:
#     """
#     強制的な順序指定のためのヘルパー関数（トラブルシューティング用）

#     Args:
#         force_order: 強制的な順序リスト
#         module_names: 全モジュールリスト

#     Returns:
#         List[str]: 解決された順序リスト
#     """
#     # プレフィックスの追加（省略時の利便性向上）
#     processed_order = []
#     for mod in force_order:
#         if not mod.startswith(ADDON_ID):
#             full_name = f"{ADDON_ID}.{mod}"
#         else:
#             full_name = mod

#         if full_name in module_names:
#             processed_order.append(full_name)
#         else:
#             print(f"警告: 指定されたモジュール {full_name} は見つかりません")

#     # 指定されていないモジュールを末尾に追加
#     remaining = [m for m in module_names if m not in processed_order]
#     return processed_order + remaining


# # ======================================================
# # 依存関係解析
# # ======================================================


# def _analyze_dependencies(module_names: List[str]) -> Dict[str, Set[str]]:
#     """
#     モジュール間の依存関係を解析
#     グラフの方向は「依存先→依存元」（被依存関係、Dependency -> Dependent）
#     """
#     print("DEBUG: Analyzing dependencies...") # DEBUG PRINT
#     # インポート依存関係 (方向: 依存元 -> 依存先)
#     import_graph_forward = _analyze_imports(module_names)
#     # ここでグラフの方向を「依存先 -> 依存元」に反転させる
#     import_graph = defaultdict(set)
#     for depender, dependencies in import_graph_forward.items():
#         for dependency in dependencies:
#             if dependency in module_names and depender in module_names: # 存在するモジュール間のみ
#                  import_graph[dependency].add(depender)
#     print(f"DEBUG:   Reversed Import graph (Dependency -> Dependent): {dict(import_graph)}") # DEBUG PRINT

#     # コード内での明示的・暗黙的依存関係 (方向: 依存先 -> 依存元)
#     graph = defaultdict(set)
#     pdtype = bpy.props._PropertyDeferred

#     # 反転させたインポート依存関係をマージ (方向: 依存先 -> 依存元)
#     print("DEBUG: Merging reversed import dependencies...") # DEBUG PRINT
#     print(f"DEBUG:   Initial graph (before merge): {dict(graph)}") # DEBUG PRINT
#     # print(f"DEBUG:   Reversed import graph to merge: {dict(import_graph)}") # DEBUG PRINT (冗長なのでコメントアウト)
#     for dependency, dependers in import_graph.items():
#         # print(f"DEBUG:     Merging dependers for {dependency}: {dependers}") # DEBUG PRINT (詳細すぎるかも)
#         before_update = graph[dependency].copy()
#         graph[dependency].update(dependers)
#         after_update = graph[dependency]
#         if before_update != after_update:
#              print(f"DEBUG:       Graph updated after merge for {dependency}: {after_update}") # DEBUG PRINT
#     print(f"DEBUG:   Graph after merging imports: {dict(graph)}") # DEBUG PRINT

#     print("DEBUG: Analyzing class property and DEPENDS_ON dependencies...") # DEBUG PRINT
#     for mod_name in module_names: # mod_name は依存元のモジュール (Dependent)
#         # print(f"DEBUG:   Analyzing module: {mod_name}") # DEBUG PRINT (冗長なのでコメントアウト)
#         mod = sys.modules.get(mod_name)
#         if not mod:
#             # print(f"DEBUG:     Module {mod_name} not found in sys.modules. Skipping.") # DEBUG PRINT
#             continue

#         # クラス依存関係解析
#         for cls_name, cls in inspect.getmembers(mod, _is_bpy_class):
#             cls_annotations = getattr(cls, "__annotations__", {})
#             for prop_name, prop in cls_annotations.items():
#                 if isinstance(prop, pdtype):
#                     prop_func = getattr(prop, "function", None)
#                     if prop_func is None and isinstance(prop, tuple):
#                         prop_func = prop[0]

#                     if prop_func in [
#                         bpy.props.PointerProperty,
#                         bpy.props.CollectionProperty,
#                     ]:
#                         dep_cls = prop.keywords.get("type")
#                         if not dep_cls:
#                             continue

#                         try:
#                             dep_mod = dep_cls.__module__ # dep_mod は依存先のモジュール (Dependency)
#                         except AttributeError:
#                             print(f"DEBUG:       WARN: Could not get __module__ for type '{dep_cls}' in {cls_name}.{prop_name}") # DEBUG PRINT
#                             continue

#                         if dep_mod == mod_name:
#                             continue

#                         # アドオン内のモジュールかチェック
#                         if dep_mod.startswith(ADDON_ID) and dep_mod in module_names:
#                             # --- ここで必ずログを出力 --- START
#                             # グラフの方向は「依存先 -> 依存元」
#                             print(f"DEBUG:       [Prop Dep Check] Adding dependency: {dep_mod} (Dep) -> {mod_name} (User) (Because {cls_name}.{prop_name} uses type {dep_cls.__name__})")
#                             # --- ここで必ずログを出力 --- END

#                             # 循環依存の特定ログ
#                             if dep_mod == f"{ADDON_ID}.preferences" and mod_name == f"{ADDON_ID}.ui.props":
#                                 print(f"DEBUG:         >>> Problematic dep condition met! preferences -> ui.props via {cls_name}.{prop_name} (type: {dep_cls.__name__})")
#                             elif dep_mod == f"{ADDON_ID}.ui.props" and mod_name == f"{ADDON_ID}.preferences":
#                                 print(f"DEBUG:         >>> Expected dep condition met! ui.props -> preferences via {cls_name}.{prop_name} (type: {dep_cls.__name__})")

#                             # 依存関係を追加 (方向: 依存先 -> 依存元)
#                             graph[dep_mod].add(mod_name)

#         # 明示的依存関係
#         if hasattr(mod, "DEPENDS_ON"):
#             dependencies_on = getattr(mod, "DEPENDS_ON")
#             print(f"DEBUG:     Found DEPENDS_ON in {mod_name}: {dependencies_on}") # DEBUG PRINT
#             for dep in dependencies_on: # dep は依存先の短縮名
#                 dep_full = f"{ADDON_ID}.{dep}"
#                 if dep_full in module_names:
#                      # 注: 方向は「依存先 -> 依存元」
#                     print(f"DEBUG:       DEPENDS_ON dep added: {dep_full} (Dep) -> {mod_name} (User)") # DEBUG PRINT
#                     graph[dep_full].add(mod_name)
#                 else:
#                     print(f"DEBUG:       WARN: DEPENDS_ON target '{dep_full}' not found in module list.") # DEBUG PRINT


#     if DBG_INIT:
#         print("\n=== 依存関係詳細 (Raw Graph, Direction: Dependency -> Dependent) ===") # DEBUG PRINT
#         # Sort graph items for consistent output
#         sorted_graph_items = sorted(graph.items())
#         for mod, deps in sorted_graph_items:
#              # Sort dependencies for consistent output
#             print(f"DEBUG:   {mod}: {sorted(list(deps))}") # DEBUG PRINT (ソートして表示)
#         print("--- End Raw Graph ---") # DEBUG PRINT

#     return graph


# def _analyze_imports(module_names: List[str]) -> Dict[str, Set[str]]:
#     """
#     インポート文から依存関係を解析する
#     Returns: Dict[str, Set[str]] 依存元 -> 依存先のグラフ (Depender -> Dependency)
#     """
#     import ast
#     print("DEBUG: Analyzing imports...") # DEBUG PRINT

#     graph = defaultdict(set) # Key: depender, Value: set of dependencies

#     for mod_name in module_names: # mod_name is the depender
#         # print(f"DEBUG:   Analyzing imports in: {mod_name}") # DEBUG PRINT (詳細すぎる場合コメントアウト)
#         mod = sys.modules.get(mod_name)
#         if not mod: continue
#         if not hasattr(mod, "__file__") or not mod.__file__: continue

#         try:
#             with open(mod.__file__, "r", encoding="utf-8") as f:
#                 content = f.read()
#             tree = ast.parse(content)

#             for node in ast.walk(tree):
#                 imported_module_name = None # 検出された依存先モジュール名 (Dependency)

#                 if isinstance(node, ast.Import):
#                     for alias in node.names:
#                         imported_name = alias.name
#                         # Check if direct import is an addon module
#                         if imported_name.startswith(ADDON_ID) and imported_name in module_names:
#                             imported_module_name = imported_name
#                             print(f"DEBUG:       [Import] Found: {mod_name} -> {imported_module_name}")
#                             graph[mod_name].add(imported_module_name)
#                         # Check if parts of the import path are addon modules (e.g., import core.utils)
#                         else:
#                             parts = imported_name.split('.')
#                             current_path = ""
#                             for i, part in enumerate(parts):
#                                 current_path = f"{current_path}.{part}" if i > 0 else part
#                                 potential_addon_module = f"{ADDON_ID}.{current_path}"
#                                 if potential_addon_module in module_names:
#                                      print(f"DEBUG:       [Import Sub] Found: {mod_name} -> {potential_addon_module}")
#                                      graph[mod_name].add(potential_addon_module)


#                 elif isinstance(node, ast.ImportFrom):
#                     level = node.level
#                     source_module_path = node.module if node.module else ""

#                     # Resolve relative path
#                     if level > 0:
#                         parent_parts = mod_name.split('.')
#                         if level >= len(parent_parts):
#                             print(f"DEBUG:     WARN: Relative import level {level} too high in {mod_name} for module '{source_module_path}'")
#                             continue
#                         base_path = '.'.join(parent_parts[:-level])
#                         resolved_source = f"{base_path}.{source_module_path}" if source_module_path else base_path
#                     else:
#                         resolved_source = source_module_path

#                     # If the resolved source is not prefixed, assume it might be an addon module
#                     potential_dependency = resolved_source
#                     if not resolved_source.startswith(ADDON_ID) and resolved_source:
#                          potential_dependency = f"{ADDON_ID}.{resolved_source}"


#                     # Check if the resolved source module itself is the dependency
#                     if potential_dependency in module_names:
#                         imported_module_name = potential_dependency
#                         print(f"DEBUG:       [ImportFrom] Found: {mod_name} -> {imported_module_name}")
#                         graph[mod_name].add(imported_module_name)

#                     # Also check imported names (e.g., from . import props -> props is not a module usually)
#                     # This part might be less relevant for module dependencies but good for completeness
#                     # for alias in node.names:
#                     #     potential_sub_module = f"{potential_dependency}.{alias.name}"
#                     #     if potential_sub_module in module_names:
#                     #          print(f"DEBUG:       [ImportFrom Name] Found: {mod_name} -> {potential_sub_module}")
#                     #          graph[mod_name].add(potential_sub_module)


#         except FileNotFoundError:
#              print(f"DEBUG:   WARN: File not found for module {mod_name}") # DEBUG PRINT
#         except SyntaxError as e:
#             print(f"DEBUG:   ERROR: Syntax error parsing {mod_name}: {e}") # DEBUG PRINT
#         except Exception as e:
#             print(f"DEBUG:   ERROR: Unexpected error analyzing imports in {mod_name}: {e}", exc_info=True) # Add exc_info

#     print("DEBUG: Import analysis finished.") # DEBUG PRINT
#     print(f"DEBUG: Import graph result (Depender -> Dependency): {dict(graph)}") # DEBUG PRINT
#     return graph


# def _sort_modules(module_names: List[str]) -> List[str]:
#     """
#     モジュールを依存関係順にソート
#     """
#     print("DEBUG: Sorting modules...") # DEBUG PRINT
#     # 依存関係解析 (方向: 依存先 -> 依存元)
#     graph = _analyze_dependencies(module_names)

#     # フィルタリング: グラフに含まれる全ノードを取得
#     print("DEBUG: Determining all nodes involved in the graph...") # DEBUG PRINT
#     nodes_in_graph = set(graph.keys())
#     for deps in graph.values():
#         nodes_in_graph.update(deps)
#     # Ensure all initially provided module_names are considered if not in graph deps
#     nodes_in_graph.update(m for m in module_names if m.startswith(ADDON_ID))
#     print(f"DEBUG:   Nodes involved in graph: {sorted(list(nodes_in_graph))}")

#     try:
#         print("DEBUG: Attempting topological sort...") # DEBUG PRINT
#         # Pass the graph (Dep -> Dependents) and all relevant nodes
#         sorted_modules = _topological_sort(graph, nodes_in_graph)
#         print("DEBUG: Topological sort successful.") # DEBUG PRINT
#         # Mermaid形式での図生成などをここに移動してもよい

#     except ValueError as e:
#         print(f"DEBUG: Topological sort failed: {e}") # DEBUG PRINT
#         print("DEBUG: Using alternative sort method.") # DEBUG PRINT
#         # alternative_sort も graph と nodes_in_graph を受け取るように調整
#         sorted_modules = _alternative_sort(graph, list(nodes_in_graph))
#         print(f"DEBUG: Alternative sort result (first 10): {sorted_modules[:10]}") # DEBUG PRINT


#     # 未処理モジュール（グラフに含まれなかったもの、または代替ソートで漏れたもの）を末尾に追加
#     processed_modules = set(sorted_modules)
#     remaining = sorted([m for m in module_names if m.startswith(ADDON_ID) and m not in processed_modules])
#     if remaining:
#         print(f"\nDEBUG: Adding modules potentially missed by sorting: {remaining}") # DEBUG PRINT
#         sorted_modules.extend(remaining)

#     print("DEBUG: Module sorting finished.") # DEBUG PRINT
#     return sorted_modules


# def _topological_sort(graph: Dict[str, Set[str]], nodes_in_graph: Set[str]) -> List[str]:
#     """
#     Kahnのアルゴリズムによるトポロジカルソート
#     グラフの方向は「依存先 (Dependency) -> 依存元 (Dependent)」を想定。
#     出力は依存先が先に来るロード順序。
#     """
#     print("DEBUG:   Running topological sort (Kahn's algorithm)...") # DEBUG PRINT

#     in_degree = defaultdict(int)
#     # Initialize in-degree for all nodes in the graph scope
#     for node in nodes_in_graph:
#         in_degree[node] = 0

#     # Calculate in-degrees based on the graph (Dependency -> Dependents)
#     for dependency in graph:
#         if dependency not in nodes_in_graph: continue # Should not happen if nodes_in_graph is correct
#         for depender in graph[dependency]:
#             if depender in nodes_in_graph:
#                 in_degree[depender] += 1
#             else:
#                 # This might indicate an issue with nodes_in_graph calculation or the graph itself
#                 print(f"DEBUG:       WARN: Depender {short_name(depender)} (dependent on {short_name(dependency)}) not in nodes_in_graph during in-degree calculation.")

#     # Start with nodes having in-degree 0
#     queue = sorted([node for node in nodes_in_graph if in_degree[node] == 0])
#     print(f"DEBUG:     Initial queue (in-degree 0): {[short_name(n) for n in queue]}") # DEBUG PRINT
#     sorted_order = []

#     processed_count = 0
#     while queue:
#         # Dequeue (dependency node)
#         node = queue.pop(0)
#         print(f"DEBUG:     Processing node: {short_name(node)}") # DEBUG PRINT
#         sorted_order.append(node)
#         processed_count += 1

#         # For each dependent node ('depender') of the current 'node' (dependency)
#         # Decrease in-degree of the depender
#         dependers = sorted(list(graph.get(node, [])))
#         for depender in dependers:
#             if depender not in nodes_in_graph:
#                 print(f"DEBUG:       WARN: Depender {short_name(depender)} (from graph[{short_name(node)}]) not found in nodes_in_graph. Skipping in-degree update.")
#                 continue

#             in_degree[depender] -= 1
#             print(f"DEBUG:       Decremented in-degree of {short_name(depender)} to {in_degree[depender]}") # DEBUG PRINT
#             if in_degree[depender] == 0:
#                 print(f"DEBUG:         Adding {short_name(depender)} to queue.") # DEBUG PRINT
#                 queue.append(depender)
#                 queue.sort() # Keep queue sorted for deterministic order
#             elif in_degree[depender] < 0:
#                  print(f"DEBUG:       WARN: In-degree of {short_name(depender)} became negative!") # DEBUG PRINT


#     # Check if all nodes were processed
#     if processed_count != len(nodes_in_graph):
#         # Identify nodes potentially in cycles (those not processed)
#         processed_set = set(sorted_order)
#         cyclic = sorted([short_name(n) for n in nodes_in_graph if n not in processed_set])
#         print(f"DEBUG:     ERROR: Topological sort failed. Nodes processed: {processed_count}, Total nodes expected: {len(nodes_in_graph)}") # DEBUG PRINT
#         print(f"DEBUG:       Nodes potentially in cycle: {cyclic}") # DEBUG PRINT
#         raise ValueError(f"循環依存検出: {', '.join(cyclic)}")

#     print("DEBUG:   Topological sort completed.") # DEBUG PRINT
#     # The sorted_order is the correct load order (dependencies first)
#     return sorted_order


# def _alternative_sort(graph: Dict[str, Set[str]], node_names: List[str]) -> List[str]:
#     """
#     循環依存がある場合の代替ソートアルゴリズム
#     node_names はグラフに含まれる全ノード名のリスト
#     """
#     print("DEBUG:   Running alternative sort...") # DEBUG PRINT
#     # ... (循環検出ログ) ...
#     try:
#         print("DEBUG:     Detecting cycles...") # DEBUG PRINT
#         # Pass the graph where keys are dependencies and values are dependents
#         cycles = _detect_cycles(graph) # _detect_cycles expects Dependency -> Dependents
#         if cycles:
#             print("\n=== 検出された循環依存 (Alternative Sort) ===")
#             for i, cycle_nodes in enumerate(cycles, 1):
#                 # Cycle nodes might not directly represent the path, but the SCC
#                 print(f"DEBUG:       Cycle Component {i}: {[short_name(n) for n in sorted(cycle_nodes)]}")
#         else:
#              print("DEBUG:     No cycles detected by _detect_cycles (but topological sort failed).") # DEBUG PRINT
#     except Exception as e:
#         print(f"DEBUG:     ERROR during cycle detection: {e}", exc_info=True)


#     # Basic priority sort (same as before, but uses node_names)
#     base_priority = { ADDON_ID: 0 }
#     priority_groups = defaultdict(list)

#     # Calculate out-degree (how many others depend on this node)
#     # This needs the graph in the other direction (Depender -> Dependency) or calculate differently
#     # Let's stick to the simple priority for now
#     for mod in node_names:
#         if mod in base_priority: priority = base_priority[mod]
#         elif ".utils." in mod or mod.endswith(".utils"): priority = 1
#         elif ".core." in mod or mod.endswith(".core"): priority = 2
#         elif ".elements." in mod or mod.endswith(".elements"): priority = 3
#         elif ".targets." in mod or mod.endswith(".targets"): priority = 4
#         elif ".ui." in mod or mod.endswith(".ui"): priority = 5
#         elif mod == f"{ADDON_ID}.preferences": priority = 6 # preferences after ui
#         else: priority = 10 # Others last

#         priority_groups[priority].append(mod)

#     result = []
#     for priority in sorted(priority_groups.keys()):
#         result.extend(sorted(priority_groups[priority]))

#     print("DEBUG:   Alternative sort finished.") # DEBUG PRINT
#     # Ensure all original nodes are included, though this simple sort should include them
#     if len(result) != len(node_names):
#          print(f"DEBUG:     WARN: Alternative sort result count ({len(result)}) differs from expected node count ({len(node_names)}).")
#     return result


# # ======================================================
# # モジュール登録/登録解除
# # ======================================================


# def register_modules() -> None:
#     """
#     全モジュールを登録

#     次の順序で登録を行います:
#     1. 全クラスを依存関係順にソート
#     2. 各クラスをBlenderに登録
#     3. 各モジュールのregister関数を呼び出し
#     """
#     if BACKGROUND and bpy.app.background:
#         return

#     classes = _get_classes()
#     success = True

#     # クラス登録
#     for cls in classes:
#         try:
#             _validate_class(cls)
#             bpy.utils.register_class(cls)
#             if DBG_INIT:
#                 print(f"✓ 登録完了: {cls.__name__}")
#         except Exception as e:
#             success = False
#             print(f"✗ クラス登録失敗: {cls.__name__}")
#             print(f"   理由: {str(e)}")
#             print(f"   モジュール: {cls.__module__}")
#             if hasattr(cls, "__annotations__"):
#                 print(f"   アノテーション: {list(cls.__annotations__.keys())}")

#     # モジュール初期化
#     for mod_name in MODULE_NAMES:
#         try:
#             mod = sys.modules[mod_name]
#             if hasattr(mod, "register"):
#                 mod.register()
#                 if DBG_INIT:
#                     print(f"✓ 初期化完了: {mod_name}")
#         except Exception as e:
#             success = False
#             print(f"✗ モジュール初期化失敗: {mod_name}")
#             print(f"   理由: {str(e)}")
#             import traceback

#             traceback.print_exc()

#     if not success:
#         print("警告: 一部コンポーネントの初期化に失敗しました")


# def unregister_modules() -> None:
#     """
#     全モジュールを登録解除

#     登録の逆順で以下を行います:
#     1. 各モジュールのunregister関数を呼び出し
#     2. 各クラスの登録解除
#     """
#     if BACKGROUND and bpy.app.background:
#         return

#     # モジュール逆初期化
#     for mod_name in reversed(MODULE_NAMES):
#         try:
#             mod = sys.modules[mod_name]
#             if hasattr(mod, "unregister"):
#                 mod.unregister()
#         except Exception as e:
#             print(f"モジュール登録解除エラー: {mod_name} - {str(e)}")

#     # クラス登録解除
#     for cls in reversed(_get_classes()):
#         try:
#             bpy.utils.unregister_class(cls)
#         except Exception as e:
#             print(f"クラス登録解除エラー: {cls.__name__} - {str(e)}")


# # ======================================================
# # ヘルパー関数
# # ======================================================


# def _collect_module_names() -> List[str]:
#     """
#     パターンに一致するモジュール名を収集

#     MODULE_PATTERNSに定義されたパターンに基づいて、
#     アドオンディレクトリ内の対象モジュールを再帰的に検索します。

#     Returns:
#         List[str]: 対象モジュール名のリスト
#     """

#     def is_masked(name: str) -> bool:
#         """指定されたモジュール名がパターンにマッチするか確認"""
#         return any(p.match(name) for p in MODULE_PATTERNS)

#     def scan(path: str, package: str) -> List[str]:
#         """指定パスからモジュールを再帰的に検索"""
#         modules = []
#         for _, name, is_pkg in pkgutil.iter_modules([path]):
#             # 非公開モジュール（_で始まる）はスキップ
#             if name.startswith("_"):
#                 continue

#             full_name = f"{package}.{name}"
#             # パッケージなら再帰的に検索
#             if is_pkg:
#                 modules.extend(scan(os.path.join(path, name), full_name))
#             # パターンにマッチするモジュールを追加
#             if is_masked(full_name):
#                 modules.append(full_name)
#         return modules

#     return scan(ADDON_PATH, ADDON_ID)


# def _get_classes(force: bool = True) -> List[bpy.types.bpy_struct]:
#     """
#     登録対象クラスを取得

#     モジュール内のBlenderクラスを抽出し、依存関係に基づいて
#     適切な順序にソートします。キャッシュ機能も備えています。

#     Args:
#         force: キャッシュを無視して再取得するか

#     Returns:
#         List[bpy.types.bpy_struct]: 依存関係順にソートされたクラスリスト
#     """
#     global _class_cache
#     if not force and _class_cache:
#         return _class_cache

#     class_deps = defaultdict(set)
#     pdtype = getattr(bpy.props, "_PropertyDeferred", tuple)

#     # クラス収集
#     all_classes = []
#     for mod_name in MODULE_NAMES:
#         mod = sys.modules[mod_name]
#         for _, cls in inspect.getmembers(mod, _is_bpy_class):
#             # クラスの依存関係を収集（プロパティの型）
#             deps = set()
#             for prop in getattr(cls, "__annotations__", {}).values():
#                 if isinstance(prop, pdtype):
#                     pfunc = getattr(prop, "function", None) or prop[0]
#                     if pfunc in (
#                         bpy.props.PointerProperty,
#                         bpy.props.CollectionProperty,
#                     ):
#                         if dep_cls := prop.keywords.get("type"):
#                             if dep_cls.__module__.startswith(ADDON_ID):
#                                 deps.add(dep_cls)
#             class_deps[cls] = deps
#             all_classes.append(cls)

#     # 依存関係ソート（深さ優先探索）
#     ordered = []
#     visited = set()
#     stack = []

#     def visit(cls):
#         """深さ優先探索による依存関係解決"""
#         if cls in stack:
#             cycle = " → ".join([c.__name__ for c in stack])
#             raise ValueError(f"クラス循環依存: {cycle}")
#         if cls not in visited:
#             stack.append(cls)
#             visited.add(cls)
#             # 依存先を先に処理
#             for dep in class_deps.get(cls, []):
#                 visit(dep)
#             stack.pop()
#             ordered.append(cls)

#     # 全クラスを処理
#     for cls in all_classes:
#         if cls not in visited:
#             visit(cls)

#     if DBG_INIT:
#         print("\n=== 登録クラス一覧 ===")
#         for cls in ordered:
#             print(f" - {cls.__name__}")

#     _class_cache = ordered
#     return ordered


# def _is_bpy_class(obj) -> bool:
#     """
#     bpy構造体クラスか判定

#     Blenderに登録可能なクラスを識別します。
#     アドオン独自のクラスのみを検出します。

#     Args:
#         obj: 判定する対象

#     Returns:
#         bool: Blenderに登録可能なクラスの場合True
#     """
#     return (
#         inspect.isclass(obj)
#         and issubclass(obj, bpy.types.bpy_struct)
#         and obj.__base__ is not bpy.types.bpy_struct
#         and obj.__module__.startswith(ADDON_ID)
#     )


# def _validate_class(cls: bpy.types.bpy_struct) -> None:
#     """
#     クラスの有効性を検証

#     Blenderに登録可能なクラスか確認します。

#     Args:
#         cls: 検証するクラス

#     Raises:
#         ValueError: bl_rna属性がない場合
#         TypeError: 適切な型でない場合
#     """
#     if not hasattr(cls, "bl_rna"):
#         raise ValueError(f"クラス {cls.__name__} にbl_rna属性がありません")
#     if not issubclass(cls, bpy.types.bpy_struct):
#         raise TypeError(f"無効なクラス型: {cls.__name__}")


# # ======================================================
# # タイムアウト管理
# # ======================================================


# class Timeout:
#     """
#     遅延実行用オペレータ

#     Blenderのイベントシステムを利用して、指定された関数を
#     一定時間後に実行します。UIスレッドのブロックを回避する
#     ために使用します。
#     """

#     bl_idname = f"{ADDON_PREFIX_PY}.timeout"
#     bl_label = ""
#     bl_options = {"INTERNAL"}

#     idx: bpy.props.IntProperty(options={"SKIP_SAVE", "HIDDEN"})
#     delay: bpy.props.FloatProperty(default=0.0001, options={"SKIP_SAVE", "HIDDEN"})

#     _data: Dict[int, tuple] = dict()  # タイムアウト関数のデータ保持用
#     _timer = None
#     _finished = False

#     def modal(self, context, event):
#         """モーダルイベント処理"""
#         if event.type == "TIMER":
#             if self._finished:
#                 context.window_manager.event_timer_remove(self._timer)
#                 del self._data[self.idx]
#                 return {"FINISHED"}

#             if self._timer.time_duration >= self.delay:
#                 self._finished = True
#                 try:
#                     func, args = self._data[self.idx]
#                     func(*args)
#                 except Exception as e:
#                     print(f"タイムアウトエラー: {str(e)}")
#         return {"PASS_THROUGH"}

#     def execute(self, context):
#         """オペレータ実行"""
#         self._finished = False
#         context.window_manager.modal_handler_add(self)
#         self._timer = context.window_manager.event_timer_add(
#             self.delay, window=context.window
#         )
#         return {"RUNNING_MODAL"}


# TimeoutOperator = type(
#     "%s_OT_timeout" % ADDON_PREFIX, (Timeout, bpy.types.Operator), {}
# )


# def timeout(func: callable, *args) -> None:
#     """
#     関数を遅延実行

#     Blenderのモーダルイベントを利用して関数を非同期で実行します。
#     UI更新や時間のかかる処理の分散に役立ちます。

#     Args:
#         func: 実行する関数
#         *args: 関数に渡す引数
#     """
#     idx = len(Timeout._data)
#     while idx in Timeout._data:
#         idx += 1
#     Timeout._data[idx] = (func, args)
#     getattr(bpy.ops, ADDON_PREFIX_PY).timeout(idx=idx)


# """
# **Modular Renamer 依存関係解析レポート**

# **1. 問題の概要**

# *   **現象**: Blenderでアドオン「Modular Renamer」をリロードする際、依存関係解析ツール (`addon.py`) が `preferences.py` と `ui/props.py` モジュール間に循環依存があるという警告を出力することがあった。
# *   **影響**: 循環依存の警告は出ていたものの、トポロジカルソート自体は（少なくとも今回のデバッグ実行時には）成功し、モジュールのロード順序は決定され、アドオンのクラス登録と初期化は完了した。これにより、アドオンは一見正常に動作しているように見える。
# *   **懸念**: 依存関係グラフに意図しない相互依存が含まれている状態は潜在的な不安定要因であり、将来的に予期せぬ問題を引き起こす可能性がある。

# **2. 調査経緯とログ分析**

# 循環依存の原因を特定するため、`addon.py` の依存関係解析関数 (`_analyze_imports`, `_analyze_dependencies`, `_topological_sort` など) に詳細なデバッグログを追加し、依存関係グラフが構築されるプロセスを追跡した。

# *   **インポート分析 (`_analyze_imports`)**:
#     *   `preferences.py` が `ui.props` を `import` している依存 (`preferences -> ui.props`) は正しく検出された。
#     *   `ui/props.py` が `preferences.py` を `import` している事実はなく、ログ上も検出されなかった。

# *   **クラスプロパティ分析 (`_analyze_dependencies`)**:
#     *   `preferences.py` 内の `CollectionProperty(type=...)` 定義に基づき、`ui.props` が `preferences` に依存している (`preferences` が `ui.props` を使用している) という依存関係 (`ui.props -> preferences`) がログ (`[Prop Dep Check]`) 上で検出され、グラフに追加された。これは期待通りの正しい動作である。
#     *   **しかし、その逆方向の依存 (`preferences -> ui.props`) がクラスプロパティ分析によって追加されていることを示すログ (`[Prop Dep Check]`) は一切確認できなかった。**

# *   **最終的な依存関係グラフ (Raw Graph)**:
#     *   `_analyze_dependencies` 関数が最終的に構築したグラフには、ログで追加が確認できなかったにも関わらず、`modular-renamer.ui.props: {..., 'modular-renamer.preferences', ...}` という **原因不明の依存関係が含まれていた**。
#     *   これにより、グラフ上では `ui.props` と `preferences` が相互に依存している状態になっていた。

# *   **トポロジカルソート (`_topological_sort`)**:
#     *   驚くべきことに、相互依存を含むグラフが入力されたにも関わらず、今回の実行ではトポロジカルソートは **成功** し、`ValueError` (循環依存エラー) は発生しなかった。これは、グラフの他の部分の構造により、たまたま循環に陥らない処理順序が見つかったためと考えられる。
#     *   これにより、以前出ていた「循環依存検出」の警告メッセージが表示されなくなった。

# **3. 結論と原因の推測**

# *   `preferences <-> ui.props` 間の相互依存がグラフに含まれることが問題の根本であるが、`ui.props -> preferences` という依存関係が**どのステップでグラフに追加されているのか、ログ上では特定できなかった** ("幽霊"依存関係)。
# *   インポート分析やクラスプロパティ分析のコード自体が直接この誤った依存を追加しているとは考えにくい。
# *   **推測される原因**:
#     1.  依存関係グラフ構築プロセス（特に `defaultdict(set)` の操作や複数ソースからの依存関係マージ）における、ログには現れない微妙な副作用。
#     2.  Blender のリロード処理に伴う Python 環境の不安定さ、`inspect` モジュールが返すクラス情報の不整合。
#     3.  `bpy.types.PropertyGroup` のメタクラス (`_RNAMetaPropGroup`) の内部的な挙動が、依存関係の解釈に予期せぬ影響を与えている可能性。

# **4. 現状と将来的な対応**

# *   **現状**: トポロジカルソートが成功し、アドオンは機能しているように見えるため、緊急の対応は不要かもしれない。ただし、グラフ内に "幽霊" 依存関係が存在する不安定な状態である。
# *   **将来的な対応**:
#     *   **再発した場合**: もし再度、循環依存エラーが発生したり、アドオンの動作が不安定になったりした場合は、以下の対応を検討する。
#         1.  **追加デバッグ**: `_analyze_dependencies` 関数の `return graph` 直前でグラフの内容を再度 `print` し、最終状態を確認する。
#         2.  **最小テストケース**: 問題を再現する最小限のモジュール構成を作成し、原因を絞り込む。
#         3.  **内部調査**: Blender のリロード機構、`inspect` モジュール、PropertyGroup の内部実装について調査する。
#     *   **より堅牢な解決策**: 原因不明の問題が解決しない場合の最終手段として、以下の方法を検討する。
#         1.  **クラス登録の委譲**: `addon.py` のクラス自動登録機能を無効化する。
#         2.  **モジュール別登録**: 各モジュール (`ui/props.py`, `preferences.py` など) が自身の `register`/`unregister` 関数を持ち、その中で `bpy.utils.register/unregister_class` を適切な順序（依存されるクラスから先に登録、逆順に解除）で呼び出すように変更する。
#         3.  **`force_order` の活用**: `addon.py` の `init_addon` で `force_order` 引数を使用し、各モジュールの `register` 関数が正しい順序で呼び出されるように制御する（特に `ui.props` の `register` が `preferences` の `register` より先に呼ばれるようにする）。

# """
