"""
命名パターン定義と名前構築処理
旧 NamingProcessor
"""

import itertools
import random
from typing import Dict, List, Optional

from ..elements.counter_element import blender_counter_element_config
from ..utils.logging import get_logger
from .element import ElementConfig, INameElement
from .element_registry import ElementRegistry

log = get_logger(__name__)


class NamingPattern:
    """
    名前を構築するための複数の要素を含む命名パターンを表す
    """

    def __init__(
        self,
        name: str,
        target_type: str,
        elements_config: List[ElementConfig],
        element_registry: ElementRegistry,
    ):
        """
        命名パターンを初期化する

        Args:
            name: パターンの名前
            elements_config: 各要素の設定リスト
            element_registry: 要素を作成するためのElementRegistry
        """
        self.name = name
        self.elements: List[INameElement] = []

        self._load_elements(elements_config, element_registry)

    def _load_elements(
        self, elements_config: List[ElementConfig], element_registry: ElementRegistry
    ) -> None:
        """
        設定から要素を読み込む

        Args:
            elements_config: 要素設定のリスト
            element_registry: 要素を作成するためのElementRegistry
        """
        for config in elements_config:
            try:
                element = element_registry.create_element(config)
                self.elements.append(element)
            except (KeyError, TypeError) as e:
                log.error(f"要素の読み込み中にエラーが発生しました: {e}")

        # かならずBlenderCounterを追加
        if "blender_counter" not in [e.element_type for e in self.elements]:
            element = element_registry.create_element(blender_counter_element_config)
            self.elements.append(element)

        # 要素を順序でソート
        self.elements.sort(key=lambda e: e.order)

    def get_element_by_id(self, element_id: str) -> INameElement:
        """
        指定されたIDの要素を取得する

        Args:
            element_id: 取得する要素のID

        Returns:
            INameElement: 見つかった要素

        Raises:
            ValueError: 要素が見つからない場合
        """
        for element in self.elements:
            if element.id == element_id:
                return element
        raise ValueError(f"要素ID {element_id} が見つかりません")

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

        log.debug(f"NamingPattern.parse_name(name={name})")
        log.debug("\n".join([f"  - {e.id}: {e.value}" for e in self.elements]))

    def update_elements(self, new_elements: Optional[Dict[str, str]] = None) -> None:
        """
        複数の要素の値を更新する

        Args:
            new_elements: 要素IDを新しい値にマッピングする辞書
        """
        if new_elements is None:
            return

        has_updated = False
        for element in self.elements:
            if element.id in new_elements:
                # new_elementsの値がNoneの場合は、その要素を無効化する
                element.set_value(new_elements[element.id] or None)
                has_updated = True

        if has_updated:
            self._notify_elements_changed()

    def _notify_elements_changed(self) -> None:
        """
        要素の変更を通知し、依存する要素を更新する

        新しい名前を生成し、その名前を使って各要素を再解析する。
        これにより、キャプチャ要素など、他の要素に依存する要素が
        更新された値で再計算される。
        """
        name = self.render_name()
        for element in self.elements:
            element.parse(name)

    def render_name(self) -> str:
        """
        パターンを名前文字列にレンダリングする

        Returns:
            レンダリングされた名前
        """
        # 有効で値を持つ要素のrender結果を収集
        # 各要素のrender()は(separator, value)のタプルを返す。
        elements_parts = [
            element.render()
            for element in self.elements
            if element.enabled and element.value
        ]

        # セパレータと値を結合して名前を生成
        name_parts = []
        for sep, value in elements_parts:
            if name_parts:  # 前の要素が存在する
                name_parts.append(sep)
            name_parts.append(value)

        name = "".join(name_parts)
        log.debug(f"render_name(): {name}")
        return name

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

    def gen_test_names(self, random: bool = False, num_cases: int = 10) -> List[str]:
        """
        テスト用の名前を生成する

        Args:
            random: ランダムな組み合わせを生成するかどうか
            num_cases: ランダムモード時の生成数

        Returns:
            List[str]: 生成されたテスト用の名前のリスト
        """
        if random:
            return self._gen_random_names(num_cases)
        else:
            return self._gen_sequential_names()

    def _gen_random_names(self, num_cases: int) -> List[str]:
        test_names = []
        for _ in range(num_cases):
            elem_parts = [
                elem.generate_random_value()
                for elem in self.elements
                if random.choice([True, False])
            ]
            name_parts = []
            for sep, value in elem_parts:
                if name_parts:
                    name_parts.append(sep)
                name_parts.append(value)
            test_names.append("".join(name_parts))
        return test_names

    def _gen_sequential_names(self) -> List[str]:
        # Generate combinations where each element is present or absent
        element_combinations = itertools.product(
            [True, False], repeat=len(self.elements)
        )
        test_names = []
        for enabled_flags in element_combinations:
            name_parts = []
            for elem, enabled in zip(self.elements, enabled_flags):
                if enabled:  # and elem.enabled:
                    sep, value = elem.generate_random_value()
                    if name_parts:
                        name_parts.append(sep)
                    name_parts.append(value)
            test_names.append("".join(name_parts))

        return test_names
