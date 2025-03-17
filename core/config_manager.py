"""
パターン設定の読み込みと永続化を管理
"""

import json
from typing import Dict, List

from ..utils.logging import get_logger
from .element import ElementConfig
from .element_registry import ElementRegistry
from .pattern import NamingPattern
from .pattern_registry import PatternRegistry

log = get_logger(__name__)


class PatternConfigManager:
    """
    パターン設定の読み込みと永続化を管理
    """

    def __init__(
        self, element_registry: ElementRegistry, pattern_registry: PatternRegistry
    ):
        self._element_registry = element_registry
        self._pattern_registry = pattern_registry

    def _convert_to_element_config(self, element_data: Dict) -> ElementConfig:
        """
        要素データからElementConfigを生成

        Args:
            element_data: 要素の設定データ

        Returns:
            ElementConfig: 要素の設定

        Raises:
            ValueError: 要素タイプが不明な場合
        """
        element_type = element_data.get("type")
        if element_type is None:
            raise ValueError("要素データにtypeフィールドが存在しません")

        element_class = self._element_registry.get_element_type(element_type)
        if element_class is None:
            raise ValueError(f"未知の要素タイプです: {element_type}")

        # 要素クラスのフィールド名を取得
        field_names = element_class.get_config_names()

        # config_fieldsに定義されたフィールドのみを抽出
        config_data = {
            field_name: element_data.get(field_name)
            for field_name in field_names
            if field_name in element_data
        }

        return ElementConfig(**config_data)

    def create_pattern(self, name: str, elements_data: List[Dict]) -> NamingPattern:
        """
        パターンを生成してレジストリに登録

        Args:
            name: パターン名
            elements_data: 要素設定のリスト

        Returns:
            NamingPattern: 生成されたパターン
        """
        elements_config = [
            self._convert_to_element_config(elem_data) for elem_data in elements_data
        ]

        pattern = NamingPattern(
            name=name,
            elements_config=elements_config,
            element_registry=self._element_registry,
        )

        self._pattern_registry.register_pattern(pattern)
        return pattern

    def load_from_file(self, path: str) -> None:
        """
        JSONファイルからパターン設定を読み込む

        Args:
            path: 設定ファイルのパス
        """
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            for pattern_data in data:
                self.create_pattern(
                    name=pattern_data["name"], elements_data=pattern_data["elements"]
                )

        except Exception as e:
            log.error(f"パターン設定の読み込みに失敗: {e}")
            raise

    def save_to_file(self, file_path: str, pattern_name: str) -> None:
        """
        パターンをJSONファイルに保存

        Args:
            file_path: 保存先ファイルパス
            pattern_name: 保存するパターンの名前

        Raises:
            ValueError: パターンが見つからない場合
        """
        pattern = self._pattern_registry.get_pattern(pattern_name)
        if pattern is None:
            raise ValueError(f"パターンが見つかりません: {pattern_name}")

        pattern_data = {"name": pattern.name, "elements": []}

        for element in pattern.elements:
            element_class = type(element)
            field_names = element_class.get_config_names()

            element_data = {
                field_name: getattr(element, field_name) for field_name in field_names
            }
            pattern_data["elements"].append(element_data)

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(pattern_data, f, indent=4)

    def save_all_patterns(self, file_path: str) -> None:
        """
        すべてのパターンをJSONファイルに保存

        Args:
            file_path: 保存先ファイルパス
        """
        patterns = self._pattern_registry.get_all_patterns()
        patterns_data = []

        for pattern in patterns:
            pattern_data = {"name": pattern.name, "elements": []}

            for element in pattern.elements:
                element_class = type(element)
                field_names = element_class.get_config_names()

                element_data = {
                    field_name: getattr(element, field_name)
                    for field_name in field_names
                }
                pattern_data["elements"].append(element_data)

            patterns_data.append(pattern_data)

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(patterns_data, f, indent=4)
