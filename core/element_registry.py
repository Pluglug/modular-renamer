"""
名前要素の登録・管理・生成
"""

from typing import Dict, Type, List
from .elements_base import INameElement, NameElement


class ElementRegistry:
    """
    設定に基づいて動的に作成できる要素タイプのレジストリ
    """

    def __init__(self):
        self._element_types: Dict[str, Type] = {}

    def register_element_type(self, type_name: str, element_class: INameElement):
        """
        レジストリに要素タイプを登録する

        Args:
            type_name: この要素タイプの一意の識別子
            element_class: この要素タイプのインスタンス化に使用するクラス
        """
        if not issubclass(element_class, INameElement):
            raise TypeError(
                f"要素クラスはINameElementインターフェースを実装する必要があります: {element_class.__name__}"
            )

        self._element_types[type_name] = element_class

    def create_element(self, type_name: str, config: dict) -> INameElement:
        """
        要素タイプと設定に基づいて要素インスタンスを作成する

        Args:
            type_name: 作成する要素のタイプ
            config: 要素の設定辞書

        Returns:
            要求された要素タイプのインスタンス

        Raises:
            KeyError: 要素タイプが登録されていない場合
        """
        if type_name not in self._element_types:
            raise KeyError(f"要素タイプが登録されていません: {type_name}")

        element_class = self._element_types[type_name]
        return element_class(config)

    def get_registered_types(self) -> List[str]:
        """
        登録されているすべての要素タイプのリストを取得する

        Returns:
            要素タイプ名のリスト
        """
        return list(self._element_types.keys())

    def validate_elements_config(self, config: List) -> List[str]:
        """
        要素設定のリストを検証する

        Args:
            config: 検証する要素設定のリスト

        Returns:
            エラーメッセージのリスト（有効な場合は空）
        """
        errors = []

        if not isinstance(config, list):
            errors.append("要素設定はリストである必要があります")
            return errors

        element_ids = set()

        for idx, element_config in enumerate(config):
            if not isinstance(element_config, dict):
                errors.append(f"インデックス {idx} の要素は辞書である必要があります")
                continue

            if "type" not in element_config:
                errors.append(f"インデックス {idx} の要素に 'type' フィールドがありません")
                continue

            element_type = element_config["type"]
            if element_type not in self._element_types:
                errors.append(f"インデックス {idx} に不明な要素タイプ '{element_type}' があります")
                continue

            if "id" not in element_config:
                errors.append(f"インデックス {idx} の要素に 'id' フィールドがありません")
                continue

            element_id = element_config["id"]
            if element_id in element_ids:
                errors.append(f"インデックス {idx} に重複した要素ID '{element_id}' があります")
            else:
                element_ids.add(element_id)

        return errors
