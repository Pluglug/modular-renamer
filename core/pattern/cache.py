import threading
from typing import List

from ..pattern.model import NamingPattern
from ...utils.logging import get_logger

log = get_logger(__name__)


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
