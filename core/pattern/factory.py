from typing import List, Optional, Protocol

from ..contracts.element import ElementConfig, INameElement
from ..element.registry import ElementRegistry
from ..pattern.model import NamingPattern
from ...elements.counter_element import blender_counter_element_config

# from ...ui.props import NamingElementProperty, NamingPatternProperty
from ...utils.logging import get_logger

log = get_logger(__name__)


class IPropertyGroup(Protocol):
    """BlenderのPropertyGroupのインターフェース"""

    id: str
    element_type: str
    order: int
    enabled: bool
    separator: str


class PatternFactory:
    """
    パターンの作成
    """

    def __init__(self, element_registry: ElementRegistry):
        self._element_registry = element_registry

    def create_pattern(self, pattern_data: "NamingPatternProperty") -> NamingPattern:
        """
        パターンを生成して返す

        Args:
            pattern_data: パターンデータ

        Returns:
            NamingPattern: 生成されたパターン
        """
        elements = self._create_elements(pattern_data)
        pattern = NamingPattern(id=pattern_data.id, elements=elements)
        return pattern

    def _create_elements(
        self, pattern_data: "NamingPatternProperty"
    ) -> List[INameElement]:
        """要素を作成"""
        elements_config = self._create_elements_config(pattern_data)
        elements = []

        for element_config in elements_config:
            try:
                element = self._element_registry.create_element(element_config)
                elements.append(element)
            except (KeyError, TypeError) as e:
                log.error(f"要素の読み込み中にエラーが発生しました: {e}")

        # かならずBlenderCounterを追加
        if "blender_counter" not in [e.element_type for e in elements]:
            element = self._element_registry.create_element(
                blender_counter_element_config
            )
            elements.append(element)

        # 要素を順序でソート
        elements.sort(key=lambda e: e.order)

        return elements

    def _create_elements_config(
        self, pattern_data: "NamingPatternProperty"
    ) -> List[ElementConfig]:
        """要素の設定を作成"""
        pattern_elements = pattern_data.elements

        elements_config = []
        for element_data in pattern_elements:
            element_config = self._convert_to_element_config(element_data)
            elements_config.append(element_config)

        return elements_config

    def _convert_to_element_config(
        self, element_data: IPropertyGroup
    ) -> Optional[ElementConfig]:
        """BlenderPropertyをElementConfigに変換"""
        element_type = element_data.element_type
        log.info(f"element_type: {element_type}")
        element_class = self._element_registry.get_element_type(element_type)

        if element_class is None:
            log.error(f"要素タイプ '{element_type}' は見つかりません")
            return None

        config_fields = element_class.config_fields

        # これで出来るはずなのだけど
        # config_data = {
        #     field_name: getattr(element_data, field_name)
        #     for field_name in config_fields
        #     if hasattr(element_data, field_name)
        # }

        # 必須パラメータを設定
        config_data = {
            "type": element_type,
            "id": getattr(element_data, "id", ""),
            "order": getattr(element_data, "order", 0),
            "enabled": getattr(element_data, "enabled", True),
            "separator": getattr(element_data, "separator", "_"),
        }

        # 追加の設定フィールドを取得
        for field_name in config_fields:
            if hasattr(element_data, field_name):
                value = getattr(element_data, field_name)
                # Blenderのプロパティコレクションをリストに変換
                if hasattr(value, "values"):
                    value = [item.name for item in value.values()]
                config_data[field_name] = value

        return ElementConfig(**config_data)
