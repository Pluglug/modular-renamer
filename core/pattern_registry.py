"""
パターンの登録・検索・保存・読み込み
古い実装では明示的に分離されていなかった機能
"""

import json
from typing import Dict, List
import os

from .pattern import NamingPattern
from .element_registry import ElementRegistry


class PatternRegistry:
    """
    異なるターゲットタイプの命名パターンを管理するレジストリ
    """

    def __init__(self, element_registry: ElementRegistry):
        """
        パターンレジストリを初期化する

        Args:
            element_registry: パターンの要素を作成するためのElementRegistry
        """
        self.patterns: Dict[str, Dict[str, NamingPattern]] = {}
        self.element_registry = element_registry

    def register_pattern(self, pattern: NamingPattern) -> None:
        """
        レジストリにパターンを登録する

        Args:
            pattern: 登録するNamingPattern
        """
        target_type = pattern.target_type

        # ターゲットタイプの辞書が存在しない場合は作成
        if target_type not in self.patterns:
            self.patterns[target_type] = {}

        # パターンを登録
        self.patterns[target_type][pattern.name] = pattern

    def get_pattern(self, target_type: str, name: str) -> NamingPattern:
        """
        ターゲットタイプと名前でパターンを取得する

        Args:
            target_type: ターゲットタイプ
            name: パターン名

        Returns:
            要求されたパターン

        Raises:
            KeyError: パターンが存在しない場合
        """
        if target_type not in self.patterns:
            raise KeyError(f"ターゲットタイプのパターンが存在しません: {target_type}")

        if name not in self.patterns[target_type]:
            raise KeyError(f"ターゲットタイプ {target_type} のパターン '{name}' が見つかりません")

        return self.patterns[target_type][name]

    def get_patterns_for_type(self, target_type: str) -> List[NamingPattern]:
        """
        ターゲットタイプのすべてのパターンを取得する

        Args:
            target_type: ターゲットタイプ

        Returns:
            ターゲットタイプのパターンリスト
        """
        if target_type not in self.patterns:
            return []

        return list(self.patterns[target_type].values())

    def load_from_file(self, path: str) -> None:
        """
        JSONファイルからパターンを読み込む

        Args:
            path: JSONファイルのパス
        """
        try:
            with open(path, "r") as f:
                data = json.load(f)

            # 既存のパターンをクリア
            self.patterns = {}

            # パターンを読み込む
            for target_type, patterns in data.items():
                for pattern_name, pattern_data in patterns.items():
                    elements_config = pattern_data.get("elements", [])
                    pattern = NamingPattern(
                        pattern_name,
                        target_type,
                        elements_config,
                        self.element_registry,
                    )
                    self.register_pattern(pattern)

        except (IOError, json.JSONDecodeError) as e:
            print(f"パターンの読み込み中にエラーが発生しました {path}: {e}")

    def save_to_file(self, path: str) -> bool:
        """
        パターンをJSONファイルに保存する

        Args:
            path: JSONファイルのパス

        Returns:
            成功した場合はTrue、それ以外はFalse
        """
        try:
            # ディレクトリが存在することを確認
            os.makedirs(os.path.dirname(path), exist_ok=True)

            # パターンをシリアライズ可能な形式に変換
            data = {}
            for target_type, patterns in self.patterns.items():
                data[target_type] = {}
                for pattern_name, pattern in patterns.items():
                    # 要素をシリアライズ
                    elements = []
                    for element in pattern.elements:
                        # 要素からシリアライズ可能なプロパティを抽出
                        # 要素にto_dictメソッドがあることを前提とする
                        elements.append(
                            {
                                "id": element.id,
                                "type": element.__class__.__name__,
                                "order": element.order,
                                "enabled": element.enabled,
                                "separator": element.separator,
                                # 追加のプロパティはここに追加
                            }
                        )

                    data[target_type][pattern_name] = {"elements": elements}

            # ファイルに書き込み
            with open(path, "w") as f:
                json.dump(data, f, indent=2)

            return True

        except (IOError, TypeError) as e:
            print(f"パターンの保存中にエラーが発生しました {path}: {e}")
            return False
