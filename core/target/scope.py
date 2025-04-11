from dataclasses import dataclass
from enum import Enum, auto
from typing import Dict, List, Set

import bpy
from bpy.types import Context

from ...utils.logging import get_logger

log = get_logger(__name__)


class CollectionSource(str, Enum):
    """データ収集元"""

    VIEW3D = "VIEW3D"
    OUTLINER = "OUTLINER"
    NODE_EDITOR = "NODE_EDITOR"
    SEQUENCE_EDITOR = "SEQUENCE_EDITOR"
    FILE_BROWSER = "FILE_BROWSER"

    def __str__(self) -> str:
        return self.value


@dataclass
class OperationScope:
    mode: CollectionSource = CollectionSource.VIEW3D
    # include_hidden: bool = False  # オプションアイディア
    # restrict_types: Optional[Set[Type]] = None  # 処理対象を限定するアイディア "OBJECT" など

    @classmethod
    def from_context(cls, context: Context) -> "OperationScope":
        # context.scene から文字列としてモードを取得
        mode_str = context.scene.rename_targets_mode

        # 文字列を CollectionSource Enum に変換
        try:
            collection_source_mode = CollectionSource[mode_str]
        except KeyError:
            # EnumProperty の定義と Scene の値が不一致の場合などのフォールバック
            log.warning(
                f"警告: 無効なモード文字列 '{mode_str}' が検出されました。デフォルトの VIEW3D を使用します。"
            )
            collection_source_mode = CollectionSource.VIEW3D

        config = {
            "mode": collection_source_mode,
            # 将来的な設定の追加
            # "include_hidden": context.scene.rename_include_hidden,
            # "restrict_types": get_restricted_types_from_context(context),
        }
        return cls(**config)


def register():
    bpy.types.Scene.rename_targets_mode = bpy.props.EnumProperty(
        name="コンテキストモード",
        description="設定するコンテキストモード",
        items=[
            (CollectionSource.VIEW3D, "3Dビュー", "3Dビューモード", "VIEW3D", 0),
            (
                CollectionSource.OUTLINER,
                "アウトライナー",
                "アウトライナーモード",
                "OUTLINER",
                1,
            ),
            (
                CollectionSource.SEQUENCE_EDITOR,
                "シーケンス",
                "シーケンスエディタモード",
                "SEQUENCE",
                2,
            ),
            (
                CollectionSource.NODE_EDITOR,
                "ノード",
                "ノードエディタモード",
                "NODETREE",
                3,
            ),
            (
                CollectionSource.FILE_BROWSER,
                "ファイル",
                "ファイルブラウザモード",
                "FILE",
                4,
            ),
        ],
        default="VIEW3D",
    )


def unregister():
    del bpy.types.Scene.rename_targets_mode
