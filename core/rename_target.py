"""
リネーム対象の統一インターフェース
旧 RenameableObject
"""

from abc import ABC, abstractmethod
from typing import Any, Set


class IRenameTarget(ABC):
    """
    リネーム可能なオブジェクトのインターフェース
    """

    @property
    @abstractmethod
    def target_type(self) -> str:
        """
        このターゲットのタイプを取得する

        Returns:
            ターゲットタイプ文字列
        """
        pass

    @property
    @abstractmethod
    def blender_object(self) -> Any:
        """
        基となるBlenderオブジェクトを取得する

        Returns:
            Blenderオブジェクト
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """
        ターゲットの現在の名前を取得する

        Returns:
            現在の名前
        """
        pass

    @abstractmethod
    def set_name(self, name: str) -> None:
        """
        ターゲットの名前を設定する

        Args:
            name: 新しい名前
        """
        pass

    @abstractmethod
    def get_namespace_key(self) -> Any:
        """
        このターゲットが属する名前空間のキーを取得する

        Returns:
            名前空間キー
        """
        pass
