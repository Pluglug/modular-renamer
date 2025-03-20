"""
パターンの登録・検索・管理
"""

from typing import Dict, List, Optional


from bpy.types import Context, PropertyGroup

from ..addon import prefs
from .pattern import NamingPattern
from .element_registry import ElementRegistry
from .element import INameElement, ElementConfig

from ..utils.logging import get_logger

log = get_logger(__name__)


# class PatternFacade:  # TODO: 作成管理のすみわけ
#     """
#     パターンの作成と管理を簡単にするFacade
#     """

#     _instance = None

#     def __new__(cls, *args, **kwargs):
#         if cls._instance is None:
#             cls._instance = super().__new__(cls)
#             cls._instance._pattern_factory = PatternFactory(ElementRegistry())
#             cls._instance._pattern_cache = PatternCache()
#             log.info("PatternFacadeが初期化されました")
#         return cls._instance

#     @classmethod
#     def get_instance(cls) -> "PatternFacade":
#         """インスタンスを取得"""
#         if cls._instance is None:
#             cls._instance = cls()
#         return cls._instance

#     def get_active_pattern(self, context: Context) -> Optional[NamingPattern]:
#         """アクティブなパターンを取得"""
#         return prefs(context).patterns[prefs(context).active_pattern_index]

#     def get_pattern(self, pattern_id: str) -> Optional[NamingPattern]:
#         """パターンを取得"""
#         return self._pattern_cache.get_pattern(pattern_id)

#     def create_pattern(self, pattern_data: PropertyGroup) -> NamingPattern:
#         """パターンを作成"""
#         return self._pattern_factory.create_pattern(pattern_data)

#     def update_pattern(self, pattern_id: str, pattern_data: PropertyGroup) -> None:
#         """パターンを更新"""
#         self._pattern_cache.update_pattern(pattern_id, pattern_data)

#     def delete_pattern(self, pattern_id: str) -> None:
#         """パターンを削除"""
#         self._pattern_cache.delete_pattern(pattern_id)

#     def get_all_patterns(self) -> List[NamingPattern]:
#         """全パターンを取得"""
#         return self._pattern_cache.get_all_patterns()

#     def clear_cache(self) -> None:
#         """キャッシュをクリア"""
#         self._pattern_cache.clear()


class PatternRegistry:  # TODO: PatternCacheに移行
    """
    パターンの登録と取得を管理する純粋なレジストリ
    設定の読み込みや永続化の詳細は上位レイヤーに委ねる
    """

    def __init__(self):
        self._patterns: Dict[str, NamingPattern] = {}
    
    def add_pattern(self, pattern: NamingPattern) -> None:
        """パターンをキャッシュに追加"""
        self._patterns[pattern.id] = pattern

    def get_pattern(self, pattern_id: str) -> Optional[NamingPattern]:
        """
        パターン名からパターンを取得

        Args:
            pattern_id: パターンID

        Returns:
            Optional[NamingPattern]: 見つかったパターン、存在しない場合はNone
        """
        return self._patterns.get(pattern_id)

    def update_pattern(self, pattern_id: str, pattern_data: PropertyGroup) -> None:
        """パターンを更新"""
        self._patterns[pattern_id] = pattern_data


    def get_all_patterns(self) -> List[NamingPattern]:
        """
        登録されている全パターンを取得

        Returns:
            List[NamingPattern]: 登録されているパターンのリスト
        """
        return list(self._patterns.values())

    def remove_pattern(self, pattern_id: str) -> None:
        """
        パターンを削除

        Args:
            pattern_id: 削除するパターンのID
        """
        self._patterns.pop(pattern_id, None)

    def clear(self) -> None:
        """全パターンの削除"""
        self._patterns.clear()


class PatternFactory:
    """
    パターンの作成
    """

    def __init__(self, element_registry: ElementRegistry):
        self._element_registry = element_registry

    def _convert_to_element_config(self, element_data: PropertyGroup) -> ElementConfig:
        """BlenderPropertyをElementConfigに変換"""
        element_type = element_data.element_type
        element_class = self._element_registry.get_element_type(element_type)

        config_fields = element_class.get_config_fields()

        config_data = {
            field_name: getattr(element_data, field_name)
            for field_name in config_fields
            if hasattr(element_data, field_name)
        }

        return ElementConfig(**config_data)

    def _create_elements_config(self, pattern_data: PropertyGroup) -> List[ElementConfig]:
        """要素の設定を作成"""

        pattern_elements = pattern_data.elements

        elements_config = []
        for element_data in pattern_elements:
            element_config = self._convert_to_element_config(element_data)
            elements_config.append(element_config)

        return elements_config

    def _create_elements(self, pattern_data: PropertyGroup) -> List[INameElement]:
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
                ElementConfig(type="blender_counter", id="blender_counter")
            )
            elements.append(element)

        # 要素を順序でソート
        elements.sort(key=lambda e: e.order)

        return elements

    def create_pattern(self, pattern_data: PropertyGroup) -> NamingPattern:
        """
        パターンを生成して返す

        Returns:
            NamingPattern: 生成されたパターン
        """
        elements = self._create_elements(pattern_data)
        pattern = NamingPattern(id=pattern_data.id, elements=elements)
        return pattern
