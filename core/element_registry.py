"""
名前要素の登録・管理・生成
"""

from typing import Dict, List, Type, Optional

from .element import INameElement, ElementData
from ..utils import logging

log = logging.getLogger(__name__)


class ElementRegistry:
    """
    設定に基づいて動的に作成できる要素タイプのレジストリ
    """

    def __init__(self):
        self._element_types: Dict[str, Type] = {}
        self._is_initialized = False

    def _initialize_default_elements(self) -> None:
        """
        デフォルトの要素タイプを自動登録する
        サブクラスを動的に検出して登録する
        """
        if self._is_initialized:
            return

        for subclass in INameElement.__subclasses__():
            element_type = getattr(subclass, "element_type", None)
            if element_type:
                try:
                    self.register_element_type(element_type, subclass)
                except TypeError as e:
                    log.warning(f"要素タイプの登録に失敗: {e}")

        self._is_initialized = True

    def register_element_type(self, type_name: str, element_class: Type[INameElement]) -> None:
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

    def create_element(self, type_name: str, element_data: ElementData) -> INameElement:
        """
        要素タイプと設定に基づいて要素インスタンスを作成する

        Args:
            type_name: 作成する要素のタイプ
            element_data: 要素の設定データ

        Returns:
            要求された要素タイプのインスタンス

        Raises:
            KeyError: 要素タイプが登録されていない場合
        """
        element_class = self.get_element_type(type_name)
        if element_class is None:
            raise KeyError(f"要素タイプが登録されていません: {type_name}")

        # if not element_data.is_valid():
        #     raise ValueError(element_data.validate(element_data))

        return element_class(element_data)

    def get_registered_types(self) -> List[str]:
        """
        登録されているすべての要素タイプのリストを取得する

        Returns:
            要素タイプ名のリスト
        """
        return list(self._element_types.keys())
