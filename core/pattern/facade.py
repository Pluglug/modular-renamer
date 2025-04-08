import json
from typing import Dict, List, Optional

from bpy.types import Context

from ...addon import prefs
from ..element.registry import ElementRegistry
from ..pattern.cache import PatternCache
from ..pattern.factory import PatternFactory
from ..pattern.model import NamingPattern
from ...ui.property_groups import NamingPatternProperty
from ...utils.logging import get_logger

log = get_logger(__name__)


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

    def create_pattern(self, pattern_data: NamingPatternProperty) -> NamingPattern:
        """パターンを作成"""
        new_pattern = self._pattern_factory.create_pattern(pattern_data)
        self._pattern_cache[pattern_data.id] = new_pattern
        return new_pattern

    def update_pattern(self, pattern_data: NamingPatternProperty) -> None:
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
        if not self._context:
            log.warning("コンテキストが無効なため同期をスキップします")
            return

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

    def _should_update_pattern(
        self, pattern: NamingPatternProperty, cached_ids: set
    ) -> bool:
        """パターンの更新が必要かどうかを判定"""
        is_new = pattern.id not in cached_ids
        return is_new or pattern.modified

    def _remove_deleted_patterns(self) -> None:
        """削除されたパターンをキャッシュから除去"""
        patterns = prefs(self._context).patterns
        prefs_pattern_ids = set(p.id for p in patterns)
        cached_pattern_ids = set(self._pattern_cache.keys())
        removed_count = 0

        for pattern_id in cached_pattern_ids - prefs_pattern_ids:
            del self._pattern_cache[pattern_id]
            removed_count += 1
            log.debug(f"パターン '{pattern_id}' がキャッシュから削除されました")

        if removed_count > 0:
            log.info(f"{removed_count}件のパターンがキャッシュから削除されました")

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
                        for field in type(element).config_fields
                    },
                }
                for element in pattern.elements
            ],
        }
