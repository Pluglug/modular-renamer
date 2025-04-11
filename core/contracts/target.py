from abc import ABC, abstractmethod
from typing import Any, ClassVar, Optional, Set, Type

import bpy
from bpy.types import ID as BlenderID
from bpy.types import Context

from ..blender.pointer_cache import PointerCache
from ..target.scope import OperationScope

from ...utils.logging import get_logger

log = get_logger(__name__)


class IRenameTarget(ABC):
    """リネーム対象インターフェース"""

    bl_type: ClassVar[str]  # Blenderでのタイプ識別子
    ol_type: ClassVar[int]  # アウトライナーでのタイプ識別子
    ol_idcode: ClassVar[int]  # アウトライナーでのIDコード (IDサブクラス以外は0)
    display_name: ClassVar[str]  # 表示名
    icon: ClassVar[str]  # アイコン名
    namespace_key: ClassVar[str]  # 名前空間のキー
    collection_type: ClassVar[Type]  # ターゲットが所属するコレクションの型

    @abstractmethod
    def get_name(self) -> str:
        """現在の名前を取得"""
        pass

    @abstractmethod
    def set_name(self, name: str, *, force_rename: bool = False) -> str:
        """名前を設定"""
        # TODO: 現段階ではForceRenameはサポートできない。
        pass

    @abstractmethod
    def get_namespace_key(self) -> str:
        """所属する名前空間のキーを取得"""
        pass

    @abstractmethod
    def create_namespace(self) -> Set[str]:
        """名前空間を作成"""
        pass

    @classmethod
    @abstractmethod
    def get_collection_type(cls):
        """収集対象のコレクションタイプを取得"""
        pass

    @classmethod
    @abstractmethod
    def can_create_from_scope(cls, source_item: Any, scope: OperationScope) -> bool:
        """指定されたソースアイテムからこのターゲットを作成できるか判定"""
        pass

    @classmethod
    @abstractmethod
    def create_from_scope(
        cls,
        context: Context,
        source_item: Any,
        scope: OperationScope,
        pointer_cache: PointerCache,
    ) -> Optional["IRenameTarget"]:
        """指定されたソースアイテムからターゲットを作成"""
        pass


class BaseRenameTarget(IRenameTarget, ABC):
    """リネームターゲットのベースクラス"""

    bl_type: str = None
    ol_type: int = None
    ol_idcode: int = None
    display_name: str = "Unknown"
    icon: str = "QUESTION"
    namespace_key: str = None
    collection_type: Type = None

    def __init__(
        self, data: Any, context: Context
    ):  # TODO: TypeVar/Genericを使ってサブクラスで具体的な型を指定できるようにする
        self._data: Any = data
        self._context: Context = context

    def get_name(self) -> str:
        return self._data.name

    def set_name(self, name: str, *, force_rename: bool = False) -> str:
        if isinstance(self._data, BlenderID) and bpy.app.version >= (
            4,
            3,
            0,
        ):  # TODO: バージョン依存を集約
            return self._data.rename(name, mode="ALWAYS" if force_rename else "NEVER")
        else:
            force_rename and log.warning(
                f"Force Rename is not supported for {self._data}"
            )
            self._data.name = name
            return "RENAMED"

    def get_namespace_key(self) -> str:
        return self.namespace_key

    @abstractmethod
    def create_namespace(self) -> Set[str]:
        pass

    @classmethod
    def get_collection_type(cls) -> Type:
        return cls.collection_type

    @classmethod
    @abstractmethod
    def can_create_from_scope(cls, source_item: Any, scope: OperationScope) -> bool:
        pass

    @classmethod
    @abstractmethod
    def create_from_scope(
        cls,
        context: Context,
        source_item: Any,
        scope: OperationScope,
        pointer_cache: PointerCache,
    ) -> Optional["IRenameTarget"]:
        pass

    def get_data(self) -> Any:
        """内部データを取得"""
        return self._data

    def __str__(self) -> str:
        """文字列表現を取得"""
        return f"{self.__class__.display_name}: {self.get_name()}"
