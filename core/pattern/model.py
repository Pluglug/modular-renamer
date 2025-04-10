import itertools
import random
from typing import Dict, List, Optional, Self

from ..contracts.element import INameElement
from ...elements.counter_element import (
    BlenderCounter,
    NumericCounter,
)
from ...utils.logging import get_logger

log = get_logger(__name__)


class NamingPattern:
    """
    名前を構築するための複数の要素を含む命名パターンを表す
    """

    def __init__(
        self,
        id: str,
        elements: List[INameElement],
    ):
        """
        命名パターンを初期化する

        Args:
            id: パターンのID
            elements: 各要素のリスト
        """
        self.id = id
        self.elements = elements

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

    def parse_name(self, name: str) -> Self:
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

        # BlenderCounterの値をNumericCounterにコピー
        blender_counter = next(
            e for e in self.elements if isinstance(e, BlenderCounter)
        )
        numeric_counter = next(
            e for e in self.elements if isinstance(e, NumericCounter)
        )  # FIXME: StopIteration: カウンター要素が無い場合(できれば必ず存在するようにしたい)
        if blender_counter.value:
            numeric_counter.take_over_counter(blender_counter)

        log.debug(f"NamingPattern.parse_name(name={name})")
        log.debug(
            "parsed elements:\n"
            + "\n".join([f"  - {e.id}: {e.value}" for e in self.elements])
        )

        return self

    def update_elements(self, new_elements: Optional[Dict[str, str]] = None) -> Self:
        """
        複数の要素の値を更新する

        Args:
            new_elements: 要素IDを新しい値にマッピングする辞書 {要素ID: 新しい値}
        """
        if new_elements is None:
            return self

        has_updated = False
        for element in self.elements:
            if element.id in new_elements:
                # new_elementsの値がNoneの場合は、その要素を無効化する
                element.set_value(new_elements[element.id] or None)
                has_updated = True

        if has_updated:
            self._notify_elements_changed()

        return self

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
        """ランダムなテスト名を生成する

        各要素をランダムに含めるか除外して名前を生成します。
        要素の順序は保持されますが、含まれる要素はランダムに決定されます。

        Args:
            num_cases: 生成するテスト名の数

        Returns:
            生成されたテスト名のリスト
        """
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
        """すべての組み合わせのテスト名を生成する

        各要素を含めるか除外するかのすべての組み合わせを生成します。
        n個の要素に対して2^n個の組み合わせが生成されます。

        Returns:
            生成されたテスト名のリスト
        """
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
