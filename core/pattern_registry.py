"""
パターンの登録・検索・管理
"""

from typing import Dict, List, Optional

from .pattern import NamingPattern


class PatternRegistry:
    """
    パターンの登録と取得を管理する純粋なレジストリ
    設定の読み込みや永続化の詳細は上位レイヤーに委ねる
    """

    def __init__(self):
        self._patterns: Dict[str, NamingPattern] = {}

    def register_pattern(self, pattern: NamingPattern) -> None:
        """
        パターンを登録

        Args:
            pattern: 登録するパターン
        """
        self._patterns[pattern.name] = pattern

    def get_pattern(self, name: str) -> Optional[NamingPattern]:
        """
        パターン名からパターンを取得

        Args:
            name: パターン名

        Returns:
            Optional[NamingPattern]: 見つかったパターン、存在しない場合はNone
        """
        return self._patterns.get(name)

    def get_all_patterns(self) -> List[NamingPattern]:
        """
        登録されている全パターンを取得

        Returns:
            List[NamingPattern]: 登録されているパターンのリスト
        """
        return list(self._patterns.values())

    def remove_pattern(self, name: str) -> None:
        """
        パターンを削除

        Args:
            name: 削除するパターンの名前
        """
        self._patterns.pop(name, None)

    def clear(self) -> None:
        """全パターンの削除"""
        self._patterns.clear()
