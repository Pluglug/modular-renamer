"""
命名パターン定義と名前構築処理
旧 NamingProcessor
"""

from typing import Dict, List, Optional

from .element_registry import ElementRegistry
from .element import INameElement


class NamingPattern:
    """
    名前を構築するための複数の要素を含む命名パターンを表す
    """

    def __init__(
        self,
        name: str,
        target_type: str,
        elements_config: List[Dict],
        element_registry: ElementRegistry,
    ):
        """
        命名パターンを初期化する

        Args:
            name: パターンの名前
            target_type: このパターンの対象タイプ（オブジェクト、ボーン、マテリアルなど）
            elements_config: 各要素の設定リスト
            element_registry: 要素を作成するためのElementRegistry
        """
        self.name = name
        self.target_type = target_type
        self.elements: List[INameElement] = []

        self._load_elements(elements_config, element_registry)

    def _load_elements(
        self, elements_config: List[Dict], element_registry: ElementRegistry
    ) -> None:
        """
        設定から要素を読み込む

        Args:
            elements_config: 要素設定のリスト
            element_registry: 要素を作成するためのElementRegistry
        """
        for config in elements_config:
            try:
                element_type = config["type"]
                element = element_registry.create_element(element_type, config)
                self.elements.append(element)
            except (KeyError, TypeError) as e:
                print(f"要素の読み込み中にエラーが発生しました: {e}")

        # 要素を順序でソート
        self.elements.sort(key=lambda e: e.order)

    def parse_name(self, name: str) -> None:
        """
        名前を解析して要素の値を抽出する

        Args:
            name: 解析する名前
        """
        # すべての要素をリセット
        for element in self.elements:
            element.standby()

        # 名前を解析
        for element in self.elements:
            element.parse(name)

    def update_elements(self, updates: Dict) -> None:
        """
        複数の要素の値を更新する

        Args:
            updates: 要素IDを新しい値にマッピングする辞書
        """
        for element_id, new_value in updates.items():
            for element in self.elements:
                if element.id == element_id:
                    element.set_value(new_value)
                    break

    def render_name(self) -> str:
        """
        パターンを名前文字列にレンダリングする

        Returns:
            レンダリングされた名前
        """
        # 値を持つ有効な要素をすべて取得
        parts = []
        for element in self.elements:
            if element.enabled:
                render_result = element.render()
                if render_result[1]:  # 値がある場合
                    separator, value = render_result
                    if parts and separator:
                        parts.append(separator)
                    parts.append(value)

        return "".join(parts)

    def validate(self) -> List[str]:
        """
        パターン設定を検証する

        Returns:
            エラーメッセージのリスト（有効な場合は空）
        """
        errors = []

        # 要素が存在するかチェック
        if not self.elements:
            errors.append("パターンに要素がありません")
            return errors

        # 重複する要素IDをチェック
        element_ids = {}
        for element in self.elements:
            if element.id in element_ids:
                errors.append(f"重複する要素ID: {element.id}")
            else:
                element_ids[element.id] = True

        # 重複する順序をチェック
        element_orders = {}
        for element in self.elements:
            if element.order in element_orders:
                errors.append(f"重複する要素順序: {element.order}")
            else:
                element_orders[element.order] = True

        return errors
