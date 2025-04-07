"""
パターンの登録・検索・管理
"""

import json
import threading
from typing import Dict, List, Optional

from bpy.types import Context, PropertyGroup

from ..addon import prefs
from ..utils.logging import get_logger
from .element import ElementConfig, INameElement
from .element_registry import ElementRegistry
from .pattern import NamingPattern
from ..elements.counter_element import blender_counter_element_config


log = get_logger(__name__)


class PatternFactory:
    """
    パターンの作成
    """

    def __init__(self, element_registry: ElementRegistry):
        self._element_registry = element_registry

    def create_pattern(self, pattern_data: PropertyGroup) -> NamingPattern:
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
                blender_counter_element_config
            )
            elements.append(element)

        # 要素を順序でソート
        elements.sort(key=lambda e: e.order)

        return elements

    def _create_elements_config(
        self, pattern_data: PropertyGroup
    ) -> List[ElementConfig]:
        """要素の設定を作成"""
        pattern_elements = pattern_data.elements

        elements_config = []
        for element_data in pattern_elements:
            element_config = self._convert_to_element_config(element_data)
            elements_config.append(element_config)

        return elements_config

    def _convert_to_element_config(self, element_data: PropertyGroup) -> ElementConfig:
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


class PatternCache:
    """
    パターンのキャッシュを保持する。
    辞書のように扱うことも可能。
    """

    _instance = None
    _lock = threading.RLock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        with self.__class__._lock:
            if not hasattr(self, "_initialized"):
                self._patterns = {}
                self._initialized = True
                log.info("PatternCacheが初期化されました")

    @classmethod
    def get_instance(cls) -> "PatternCache":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    @classmethod
    def reset_instance(cls):
        with cls._lock:
            cls._instance = None

    def __getitem__(self, pattern_id: str) -> NamingPattern:
        """
        パターンを辞書形式で取得 (cache[pattern_id])

        Args:
            pattern_id: パターンID

        Returns:
            NamingPattern: 見つかったパターン

        Raises:
            KeyError: パターンが存在しない場合
        """
        pattern = self._patterns.get(pattern_id)
        if pattern is None:
            raise KeyError(f"パターン '{pattern_id}' は存在しません")
        return pattern

    def __setitem__(self, pattern_id: str, pattern: NamingPattern) -> None:
        """
        パターンを辞書形式で設定 (cache[pattern_id] = pattern)

        Args:
            pattern_id: パターンID
            pattern: 登録するパターン
        """
        with self.__class__._lock:
            if pattern.id != pattern_id:
                raise ValueError(
                    f"パターンIDが一致しません: {pattern_id} != {pattern.id}"
                )
            self._patterns[pattern_id] = pattern

    def __delitem__(self, pattern_id: str) -> None:
        """
        パターンを辞書形式で削除 (del cache[pattern_id])

        Args:
            pattern_id: 削除するパターンID

        Raises:
            KeyError: パターンが存在しない場合
        """
        with self.__class__._lock:
            if pattern_id not in self._patterns:
                raise KeyError(f"パターン '{pattern_id}' は存在しません")
            del self._patterns[pattern_id]

    def __contains__(self, pattern_id: str) -> bool:
        """
        パターンの存在確認 (pattern_id in cache)

        Args:
            pattern_id: 確認するパターンID

        Returns:
            bool: パターンが存在するかどうか
        """
        return pattern_id in self._patterns

    def __iter__(self):
        """
        イテレータとして使用 (for pattern_id in cache)

        Returns:
            Iterator: パターンIDのイテレータ
        """
        return iter(self._patterns)

    def keys(self) -> List[str]:
        """
        パターンIDのリストを取得

        Returns:
            List[str]: パターンIDのリスト
        """
        return list(self._patterns.keys())

    def __len__(self) -> int:
        """
        パターン数を取得 (len(cache))

        Returns:
            int: パターン数
        """
        return len(self._patterns)

    def values(self) -> List[NamingPattern]:
        """
        全パターンを取得

        Returns:
            List[NamingPattern]: 登録されているパターンのリスト
        """
        return list(self._patterns.values())

    def clear(self) -> None:
        """全パターンの削除"""
        with self.__class__._lock:
            self._patterns.clear()


class PatternFacade:
    """
    パターンの作成と管理
    Blenderのプリファレンスとの同期を管理
    """

    def __init__(self, context: Context):
        self._context = context
        self._pattern_factory = PatternFactory(ElementRegistry.get_instance())
        self._pattern_cache = PatternCache.get_instance()

        # ElementRegistryの初期化を確実に行う
        element_registry = ElementRegistry.get_instance()
        if not element_registry._is_initialized:
            element_registry._initialize_default_elements()

        if not self._pattern_cache:
            log.info("キャッシュが空のため同期を行います")
            self.synchronize_patterns()

        log.info("PatternFacadeが初期化されました")

    # def _create_default_patterns(self) -> None:
    #     """デフォルトパターンを作成"""
    #     try:
    #         # デフォルトパターンの定義
    #         default_patterns = [
    #             {
    #                 "id": "pose_bone_default",
    #                 "elements": [
    #                     {
    #                         "element_type": "text",
    #                         "id": "prefix",
    #                         "order": 0,
    #                         "enabled": True,
    #                         "separator": "",
    #                         "items": ["Bone"]
    #                     },
    #                     {
    #                         "element_type": "position",
    #                         "id": "position",
    #                         "order": 1,
    #                         "enabled": True,
    #                         "separator": "_"
    #                     },
    #                     {
    #                         "element_type": "blender_counter",
    #                         "id": "counter",
    #                         "order": 2,
    #                         "enabled": True,
    #                         "separator": "",
    #                         "digits": 2
    #                     }
    #                 ]
    #             }
    #         ]

    #         # デフォルトパターンを作成
    #         for pattern_data in default_patterns:
    #             try:
    #                 pattern = self._pattern_factory.create_pattern(pattern_data)
    #                 self._pattern_cache[pattern_data["id"]] = pattern
    #                 log.info(f"デフォルトパターン '{pattern_data['id']}' を作成しました")
    #             except Exception as e:
    #                 log.error(f"デフォルトパターン '{pattern_data['id']}' の作成に失敗: {e}")

    #     except Exception as e:
    #         log.error(f"デフォルトパターンの作成に失敗: {e}")

    # パターン管理
    def get_active_pattern(self) -> Optional[NamingPattern]:
        """アクティブなパターンを取得"""
        try:
            pr = prefs(self._context)
            active_pattern = pr.get_active_pattern()
            if not active_pattern:
                return None
            return self._pattern_cache[active_pattern.id]
        except Exception as e:
            log.error(f"アクティブパターンの取得中にエラーが発生しました: {e}")
            return None

    def get_pattern(self, pattern_id: str) -> Optional[NamingPattern]:
        """パターンを取得"""
        try:
            return self._pattern_cache[pattern_id]
        except KeyError:
            return None

    def create_pattern(self, pattern_data: PropertyGroup) -> NamingPattern:
        """パターンを作成"""
        new_pattern = self._pattern_factory.create_pattern(pattern_data)
        self._pattern_cache[pattern_data.id] = new_pattern
        return new_pattern

    def update_pattern(self, pattern_data: PropertyGroup) -> None:
        """
        パターンを更新

        Args:
            pattern_data: 新しいパターンデータ
        """
        # 既存のパターンを削除（存在する場合）
        if pattern_data.id in self._pattern_cache:
            del self._pattern_cache[pattern_data.id]

        # 新しいパターンを作成して登録
        self.create_pattern(pattern_data)

        # 変更フラグをリセット
        pattern_data.modified = False

        log_message = (
            "新規パターン" if pattern_data.id not in self._pattern_cache else "更新"
        )
        log.info(f"{log_message} '{pattern_data.id}' が登録されました")

    def delete_pattern(self, pattern_id: str) -> None:
        """パターンを削除"""
        try:
            del self._pattern_cache[pattern_id]
        except KeyError:
            pass

    def get_all_patterns(self) -> List[NamingPattern]:
        """全パターンを取得"""
        return self._pattern_cache.values()

    # 同期処理
    def synchronize_patterns(self) -> None:
        """
        キャッシュとパターンの同期処理

        1. 新規・変更パターンの作成と登録
        2. 削除されたパターンの除去
        """
        self._synchronize_modified_patterns()
        self._remove_deleted_patterns()

    def _synchronize_modified_patterns(self) -> None:
        """新規または変更されたパターンを同期"""
        patterns = prefs(self._context).patterns
        cached_pattern_ids = set(self._pattern_cache.keys())

        for pattern in patterns:
            if self._should_update_pattern(pattern, cached_pattern_ids):
                try:
                    log.debug(f"Updating pattern: {pattern.id}")
                    self.update_pattern(pattern)
                except Exception as e:
                    log.error(
                        f"パターン '{pattern.id}' の同期中にエラーが発生しました: {e}"
                    )
                    continue

        # キャッシュの整合性を確認
        for pattern_id in cached_pattern_ids:
            if pattern_id not in [p.id for p in patterns]:
                log.debug(f"削除されたパターンをキャッシュから削除: {pattern_id}")
                del self._pattern_cache[pattern_id]

    def _should_update_pattern(self, pattern: PropertyGroup, cached_ids: set) -> bool:
        """パターンの更新が必要かどうかを判定"""
        is_new = pattern.id not in cached_ids
        return is_new or pattern.modified

    def _remove_deleted_patterns(self) -> None:
        """削除されたパターンをキャッシュから除去"""
        patterns = prefs(self._context).patterns
        prefs_pattern_ids = set(p.id for p in patterns)
        cached_pattern_ids = set(self._pattern_cache.keys())

        for pattern_id in cached_pattern_ids - prefs_pattern_ids:
            del self._pattern_cache[pattern_id]
            log.info(f"パターン '{pattern_id}' がキャッシュから削除されました")

    # キャッシュ管理
    def clear_cache(self) -> None:
        """キャッシュをクリア"""
        self._pattern_cache.clear()

    # TODO: SRPの違反 PatternSerializerに分離
    def load_from_file(self, path: str) -> None:
        """JSONファイルからパターン設定を読み込む"""
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            for pattern_data in data:
                self.create_pattern(pattern_data)

        except Exception as e:
            log.error(f"パターン設定の読み込みに失敗: {e}")
            raise

    def save_to_file(self, file_path: str, pattern_id: str) -> None:
        """パターンをJSONファイルに保存"""
        try:
            pattern = self._pattern_cache[pattern_id]
            pattern_data = self._convert_pattern_to_dict(pattern)

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(pattern_data, f, indent=4)
        except KeyError:
            raise ValueError(f"パターンが見つかりません: {pattern_id}")

    def save_all_patterns(self, file_path: str) -> None:
        """すべてのパターンをJSONファイルに保存"""
        patterns_data = [
            self._convert_pattern_to_dict(pattern)
            for pattern in self._pattern_cache.values()
        ]

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(patterns_data, f, indent=4)

    def _convert_pattern_to_dict(self, pattern: NamingPattern) -> Dict:
        """パターンを辞書形式に変換"""
        return {
            "id": pattern.id,
            "elements": [
                {
                    "type": element.element_type,
                    **{
                        field: getattr(element, field)
                        for field in type(element).get_config_names()
                    },
                }
                for element in pattern.elements
            ],
        }
