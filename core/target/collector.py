from typing import Any, Dict, List, Optional, Set, Type, Union

import bpy
from bpy.types import Context, EditBone, Node, Object, PoseBone

from ..blender.outliner_access import (
    OutlinerElementInfo,
    get_selected_outliner_elements,
)
from ..blender.pointer_cache import PointerCache
from ..constants import get_selected_sequences, BlenderTypeProvider
from ..contracts.target import IRenameTarget
from ..target.registry import RenameTargetRegistry
from ..target.scope import CollectionSource, OperationScope


class TargetCollector:
    """リネーム対象収集クラス"""

    def __init__(self, context: Context, scope: OperationScope):
        self.context = context
        self.scope = scope
        self.registry = RenameTargetRegistry.get_instance()
        self.pointer_cache = PointerCache(context)

    def _get_override_dict_for_area_type(
        self, area_type: str
    ):  # TODO: ScreenUtilsに移行
        """指定されたエリアタイプのコンテキストオーバーライド用の辞書を取得"""
        if not self.context.window_manager:
            return None
        for window in self.context.window_manager.windows:
            for area in window.screen.areas:
                if area.type == area_type:
                    return {"window": window, "area": area, "region": area.regions[-1]}
        return None

    def get_selected_items(self) -> List[Any]:
        """指定されたモードから選択アイテムを取得"""
        try:
            mode_dispatcher = {
                CollectionSource.VIEW3D: self._get_selected_from_view3d,
                CollectionSource.OUTLINER: self._get_selected_from_outliner,
                CollectionSource.NODE_EDITOR: self._get_selected_from_node_editor,
                CollectionSource.SEQUENCE_EDITOR: self._get_selected_from_sequence_editor,
                CollectionSource.FILE_BROWSER: self._get_selected_from_file_browser,
            }
            if handler := mode_dispatcher.get(self.scope.mode):
                return handler()
            else:
                raise ValueError(f"サポートされていないソースタイプ: {self.scope.mode}")

        except Exception as e:
            print(f"選択要素の取得中にエラーが発生しました: {str(e)}")
            return []

    def _get_selected_from_view3d(self) -> List[Union[Object, PoseBone, EditBone]]:
        """View3Dから選択された要素を取得"""
        if not self.context.active_object:
            return []

        if self.context.mode == "OBJECT":
            return self.context.selected_objects or []

        if (
            self.context.active_object.type != "ARMATURE"
            or not self.context.active_bone
        ):
            return []

        mode_dispatch = {
            "POSE": self.context.selected_pose_bones,
            "EDIT_ARMATURE": self.context.selected_bones,
        }
        return mode_dispatch.get(self.context.mode, [])

    def _get_selected_from_outliner(self) -> List[OutlinerElementInfo]:
        """アウトライナーから選択された要素を取得 (未実装)"""
        return get_selected_outliner_elements(self.context)

    def _get_selected_from_node_editor(self) -> List[Node]:
        """ノードエディタから選択された要素を取得"""

        if (
            self.context.area and self.context.area.type == "NODE_EDITOR"
        ):  # 将来的にNodeEditorにもパネルを実装する
            return self.context.selected_nodes or []

        # View3D Toolパネル用の実装
        if ctx_dict := self._get_override_dict_for_area_type("NODE_EDITOR"):
            with self.context.temp_override(**ctx_dict):
                return self.context.selected_nodes or []
        return []

    def _get_selected_from_sequence_editor(self) -> List[Any]:
        """シーケンスエディタから選択された要素を取得"""

        if ctx_dict := self._get_override_dict_for_area_type("SEQUENCE_EDITOR"):
            with self.context.temp_override(**ctx_dict):
                return get_selected_sequences(self.context)
        return []

    def _get_selected_from_file_browser(self) -> List[Any]:
        """ファイルブラウザから選択された要素を取得"""
        if ctx_dict := self._get_override_dict_for_area_type("FILE_BROWSER"):
            with self.context.temp_override(**ctx_dict):
                return self.context.selected_files or []
        return []

    def collect_targets(self) -> List[IRenameTarget]:
        """指定されたモードからリネーム対象を収集"""
        # TODO: バッチ処理や最大数の制限を検討

        # 1. 一次情報の収集
        targets: List[IRenameTarget] = []
        primary_items = self.get_selected_items()

        if not primary_items:
            return []

        # --- 2. 必要なキャッシュタイプの特定 (1回目のループ) ---
        required_types: Set[Type] = set()
        target_class_map: Dict[int, Optional[Type[IRenameTarget]]] = (
            {}
        )  # item とクラスのマッピングを一時保存

        for idx, item in enumerate(primary_items):
            target_cls = self.registry.find_target_class_for_item(item, self.scope)
            target_class_map[idx] = target_cls

            if target_cls:
                # このクラスが必要とするコレクションタイプを取得
                collection_type = target_cls.get_collection_type()
                if collection_type:
                    required_types.add(collection_type)

        # --- 3. CacheManagerにキャッシュ構築を指示 ---
        if required_types:
            print(f"Collector: Requesting cache for types: {required_types}")  # Debug
            self.pointer_cache.ensure_pointer_cache_for_types(required_types)
        else:
            print("Collector: No required types identified for caching.")  # Debug

        # --- 4. IRenameTargetインスタンスの生成 (2回目のループ) ---
        for idx, item in enumerate(primary_items):
            target_cls = target_class_map.get(idx)

            if target_cls:
                try:
                    target_instance = target_cls.create_from_scope(
                        self.context, item, self.scope, self.pointer_cache
                    )
                    if target_instance:
                        targets.append(target_instance)
                except Exception as e:
                    print(
                        f"エラー: ターゲット '{target_cls.__name__}' の生成に失敗しました ({item}): {e}"
                    )
                    import traceback

                    traceback.print_exc()

        return targets
