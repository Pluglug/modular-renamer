"""
リネーム対象の統一インターフェース
旧 RenameableObject
"""

import inspect
from abc import ABC, abstractmethod
from typing import Any, ClassVar, Dict, List, Optional, Set, Tuple, Type

from bpy.types import Context

from ..utils.logging import get_logger
from ..utils.strings_utils import is_pascal_case, to_snake_case

log = get_logger(__name__)


class IRenameTarget(ABC):
    """
    リネーム可能なオブジェクトのインターフェース
    """

    target_type: ClassVar[str]

    @abstractmethod
    def get_name(self) -> str:
        """
        ターゲットの現在の名前を取得する

        Returns:
            現在の名前
        """
        pass

    @abstractmethod
    def set_name(self, name: str) -> None:
        """
        ターゲットの名前を設定する

        Args:
            name: 新しい名前
        """
        pass

    @abstractmethod
    def get_namespace_key(self) -> str:
        """
        このターゲットが属する名前空間のキーを取得する

        Returns:
            名前空間キー
        """
        pass

    @abstractmethod
    def get_blender_object(self) -> Any:
        """
        基となるBlenderオブジェクトを取得する

        Returns:
            Blenderオブジェクト
        """
        pass

    @abstractmethod
    def create_namespace(self, context: Any) -> "INamespace":
        """
        このターゲットの名前空間を作成する

        Returns:
            INamespaceのインスタンス
        """
        pass


class BaseRenameTarget(IRenameTarget):
    """
    リネーム可能なオブジェクトの基本実装
    """

    @classmethod
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if not hasattr(cls, "target_type"):
            name = cls.__name__.replace("RenameTarget", "")
            if is_pascal_case(name):
                cls.target_type = to_snake_case(name)
            else:
                log.warning(f"PascalCaseではない要素名: {name}")
                cls.target_type = name.lower()

    def __init__(self, blender_obj: Any):
        self._blender_obj = blender_obj

    def get_name(self) -> str:
        return self._blender_obj.name

    def set_name(self, name: str) -> None:
        self._blender_obj.name = name

    def get_namespace_key(self) -> str:
        return self.target_type

    def get_blender_object(self) -> Any:
        return self._blender_obj

    @abstractmethod
    def create_namespace(self, context: Context) -> "INamespace":
        """
        このターゲットの型に対応する名前空間を作成する
        サブクラスでオーバーライドする必要がある

        Args:
            context: Blenderコンテキスト

        Returns:
            作成された名前空間

        Raises:
            NotImplementedError: サブクラスで実装されていない場合
        """
        raise NotImplementedError(
            f"{self.__class__.__name__}のcreate_namespaceメソッドが実装されていません"
        )


class TargetRegistry:
    """
    ターゲットタイプと名前空間タイプの登録を管理するレジストリ
    """

    _instance = None

    @classmethod
    def get_instance(cls):
        """
        TargetRegistryのシングルトンインスタンスを取得する

        Returns:
            TargetRegistryのインスタンス
        """
        if cls._instance is None:
            cls._instance = TargetRegistry()
            cls._instance._initialize_defaults()
        return cls._instance

    @classmethod
    def reset_instance(cls):
        """
        TargetRegistryのインスタンスをリセットする(テスト用)
        """
        cls._instance = None

    def __init__(self):
        """
        TargetRegistryを初期化する
        """
        self._target_types: Dict[str, Type[IRenameTarget]] = {}

    def _initialize_defaults(self):
        """
        デフォルトのターゲットタイプと名前空間タイプを登録する
        """
        for subclass in IRenameTarget.__subclasses__():
            if inspect.isabstract(subclass):
                continue
            self.register_target_type(subclass.target_type, subclass)

    def register_target_type(
        self, type_name: str, target_class: Type[IRenameTarget]
    ) -> None:
        """
        ターゲットタイプを登録する

        Args:
            type_name: ターゲットタイプの名前
            target_class: ターゲットタイプのクラス
        """
        self._target_types[type_name] = target_class

    def create_target(
        self, type_name: str, blender_obj: Any
    ) -> Optional[IRenameTarget]:
        """
        指定されたタイプのターゲットを作成する

        Args:
            type_name: ターゲットタイプの名前
            blender_obj: Blenderオブジェクト

        Returns:
            作成されたターゲット、またはNone（タイプが見つからない場合）
        """
        target_class = self._target_types.get(type_name)
        if not target_class:
            return None
        return target_class(blender_obj)

    def get_registered_target_types(self) -> List[str]:
        """
        登録されているターゲットタイプの一覧を取得する

        Returns:
            ターゲットタイプ名のリスト
        """
        return list(self._target_types.keys())
