"""
名前要素の登録・管理・生成
"""

import inspect
from typing import Dict, List, Optional, Type

from ..utils import logging
from .element import ElementData, INameElement

log = logging.getLogger(__name__)


class ElementRegistry:
    """
    設定に基づいて動的に作成できる要素タイプのレジストリ
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._element_types = {}
            cls._instance._is_initialized = False
        return cls._instance

    def __init__(self):
        pass

    @classmethod
    def get_instance(cls) -> "ElementRegistry":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls):
        cls._instance = None

    def _initialize_default_elements(self) -> None:
        """
        デフォルトの要素タイプを自動登録する
        具象クラスのみを登録する
        """
        if self._is_initialized:
            return

        for subclass in INameElement.__subclasses__():

            # 抽象基底クラスは除外
            if subclass.__base__ is INameElement or inspect.isabstract(subclass):
                log.debug(f"除外: {subclass.__name__}")
                continue

            element_type = getattr(subclass, "element_type", None)
            if element_type:
                try:
                    self.register_element_type(element_type, subclass)
                except TypeError as e:
                    log.warning(f"要素タイプの登録に失敗: {e}")

        self._is_initialized = True

    def register_element_type(
        self, type_name: str, element_class: Type[INameElement]
    ) -> None:
        """
        レジストリに要素タイプを登録する

        Args:
            type_name: この要素タイプの一意の識別子
            element_class: この要素タイプのインスタンス化に使用するクラス

        Raises:
            TypeError: クラスがINameElementを実装していない場合
            ValueError: 既に登録済みの型名の場合
        """
        if not issubclass(element_class, INameElement):
            raise TypeError(
                f"要素クラスはINameElementインターフェースを実装する必要があります: {element_class.__name__}"
            )

        if type_name in self._element_types:
            raise ValueError(f"要素タイプ '{type_name}' は既に登録されています")

        self._element_types[type_name] = element_class

    def get_element_type(self, type_name: str) -> Optional[Type[INameElement]]:
        """
        登録された要素タイプを取得する
        存在しない場合はデフォルト要素の初期化を試みる

        Args:
            type_name: 取得する要素タイプの名前

        Returns:
            要素クラス、存在しない場合はNone
        """
        if not self._is_initialized:
            self._initialize_default_elements()

        return self._element_types.get(type_name, None)

    def create_element(self, element_data: ElementData) -> INameElement:
        """
        要素タイプと設定に基づいて要素インスタンスを作成する

        Args:
            element_data: 要素の設定データ

        Returns:
            要求された要素タイプのインスタンス

        Raises:
            KeyError: 要素タイプが登録されていない場合
        """
        if not element_data.is_valid():
            raise ValueError(element_data.validate(element_data))

        element_class = self.get_element_type(element_data.type)
        if element_class is None:
            raise KeyError(f"要素タイプが登録されていません: {element_data.type}")

        return element_class(element_data)

    def get_registered_types(self) -> List[str]:
        """
        登録されているすべての要素タイプのリストを取得する

        Returns:
            要素タイプ名のリスト
        """
        return list(self._element_types.keys())
