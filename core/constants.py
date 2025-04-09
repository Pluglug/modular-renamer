from typing import Any, Dict, List, Optional, Set, Type, Union

import bpy
from bpy.types import Context

# RENAMABLE_OBJECT_TYPES = [
#     ("POSE_BONE", "Pose Bone", "Rename pose bones"),
#     ("OBJECT", "Object", "Rename objects"),
#     ("MATERIAL", "Material", "Rename materials"),
# ]

# Default separator options
SEPARATOR_ITEMS = [
    ("_", "Underscore", "_"),
    (".", "Dot", "."),
    ("-", "Dash", "-"),
    (" ", "Space", " "),
]

ELEMENT_TYPE_ITEMS = [
    ("text", "Text", "Normal text with predefined options"),
    # ("free_text", "Free Text", "Any text input"),  # 未実装
    ("position", "Position", "Positional indicators (L/R, Top/Bot, etc)"),
    ("numeric_counter", "Numeric Counter", "Numerical counter with formatting options"),
    # (
    #     "alphabetic_counter",
    #     "Alphabetic Counter",
    #     "Alphabetic counter with formatting options",
    # ),
    # ("date", "Date", "Date in various formats"),  # 未実装
    # ("regex", "RegEx", "Custom regular expression pattern"),  # 未実装
]

# Position enum items organized by axis
POSITION_ENUM_ITEMS = {
    "XAXIS": [
        ("L|R", "L / R", "Upper case L/R", 1),
        ("l|r", "l / r", "Lower case l/r", 2),
        ("LEFT|RIGHT", "LEFT / RIGHT", "Full word LEFT/RIGHT", 3),
        ("Left|Right", "Left / Right", "Full word Left/Right", 4),
        ("left|right", "left / right", "Full word left/right", 5),
    ],
    "YAXIS": [
        ("Top|Bot", "Top / Bot", "Upper case Top/Bot", 1),
    ],
    "ZAXIS": [
        ("Fr|Bk", "Fr / Bk", "Upper case Fr/Bk", 1),
    ],
}


# Blenderバージョン依存型の管理
class BlenderTypeProvider:
    """Blenderのバージョンに応じた型プロバイダ"""

    _instance: Optional["BlenderTypeProvider"] = None

    @classmethod
    def get_instance(cls) -> "BlenderTypeProvider":
        """シングルトンインスタンスを取得"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """シングルトンインスタンスをリセット"""
        cls._instance = None

    def __init__(self):
        self._version = bpy.app.version
        self._cache = {}

    def get_sequence_type(self) -> Type:
        """シーケンスの型を取得 (Blender 4.4から変更)"""
        if not self._cache.get("sequence_type"):
            if self._version < (4, 4, 0):
                try:
                    from bpy.types import Sequence

                    self._cache["sequence_type"] = Sequence
                except ImportError:
                    # フォールバック：何らかの理由でインポートできない場合は型をモックする
                    print(
                        "警告: bpy.types.Sequence をインポートできません。モック化します。"
                    )
                    self._cache["sequence_type"] = type("MockSequence", (), {})
            else:
                try:
                    from bpy.types import Strip

                    self._cache["sequence_type"] = Strip
                except ImportError:
                    # フォールバック：何らかの理由でインポートできない場合は型をモックする
                    print(
                        "警告: bpy.types.Strip をインポートできません。モック化します。"
                    )
                    self._cache["sequence_type"] = type("MockStrip", (), {})
        return self._cache["sequence_type"]

    def get_sequence_type_name(self) -> str:
        """シーケンスの型名を取得"""
        if self._version < (4, 4, 0):
            return "Sequence"
        else:
            return "Strip"

    def get_selected_sequences(self, context) -> List[Any]:
        """コンテキストからバージョンに応じたシーケンス選択要素を取得"""
        if self._version < (4, 4, 0):
            return context.selected_sequences or []
        else:
            return context.selected_strips or []


# グローバルなショートカット関数
def get_sequence_type() -> Type:
    """シーケンスの型を取得するショートカット関数"""
    return BlenderTypeProvider.get_instance().get_sequence_type()


def get_sequence_type_name() -> str:
    """シーケンスの型名を取得するショートカット関数"""
    return BlenderTypeProvider.get_instance().get_sequence_type_name()


def get_selected_sequences(context) -> List[Any]:
    """コンテキストからバージョンに応じたシーケンス選択要素を取得するショートカット関数"""
    return BlenderTypeProvider.get_instance().get_selected_sequences(context)


# モジュール初期化時に型プロバイダを初期化
_provider = BlenderTypeProvider.get_instance()
SequenceType = _provider.get_sequence_type()
