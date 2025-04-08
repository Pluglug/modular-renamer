from abc import ABC, abstractmethod

from .element import BaseElement, ElementConfig
from ...utils.logging import get_logger

log = get_logger(__name__)


class ICounter(ABC):
    """Interface for all counter types"""

    @property
    @abstractmethod
    def value(self) -> str | None:
        """Get counter's string value"""
        pass

    @property
    @abstractmethod
    def value_int(self) -> int | None:
        """Get counter's integer value"""
        pass

    @value_int.setter
    @abstractmethod
    def value_int(self, value: int | None) -> None:
        """Set counter's integer value"""
        pass

    @abstractmethod
    def set_value(self, new_value: str | None) -> None:
        """Set counter's string value"""
        pass

    @abstractmethod
    def add(self, value: int) -> None:
        """Add a value to the counter"""
        pass

    @abstractmethod
    def increment(self) -> None:
        """Increment counter value"""
        pass

    @abstractmethod
    def format_value(self, value: int) -> str:
        """Format an integer value according to counter rules"""
        pass

    @abstractmethod
    def gen_proposed_name(self, value: int) -> str:
        """Generate proposed name with given counter value"""
        pass

    @abstractmethod
    def take_over_counter(self, other: "ICounter", force: bool = False) -> None:
        """Take over counter from another counter"""
        pass


class BaseCounter(BaseElement, ICounter):
    """Base implementation for all counters"""

    def __init__(self, element_config: ElementConfig):
        super().__init__(element_config)
        self._value_int = None
        self.forward = None
        self.backward = None

    # TODO: INameElementとICounterを継承して、BaseCounterを作成する

    @property
    def value_int(self) -> int | None:
        return self._value_int

    @value_int.setter
    def value_int(self, value: int | None) -> None:
        if value is not None:
            self._value_int = value
            self._value = self.format_value(value)
        else:
            self._value_int = None
            self._value = None

    def set_value(self, new_value: str | None) -> None:
        """BaseElementのset_valueをオーバーライドして値の同期を保証"""
        if new_value is None:
            self._value = None
            self._value_int = None
        elif isinstance(new_value, int):
            # 整数の場合はvalue_intを通して値を更新
            self.value_int = new_value
        elif isinstance(new_value, str):
            try:
                # まずBaseElementの_valueを更新
                self._value = new_value
                # 文字列を整数に変換
                value_int = self._parse_value(new_value)
                # _value_intも更新（_valueは既に設定済みなので上書きしない）
                self._value_int = value_int
            except ValueError:
                log.error(f"Value '{new_value}' cannot be converted to counter value.")
                self._value = new_value  # 変換に失敗しても文字列値は保持
                self._value_int = None  # 数値表現はクリア
        else:
            # 非対応の型の場合
            super().set_value(new_value)  # BaseElementの実装に任せる
            self._value_int = None  # 数値表現はクリア

    def add(self, value: int) -> None:
        """Add a value to the counter"""
        if self._value_int is None:
            self.value_int = value
        else:
            self.value_int = self._value_int + value

    def increment(self) -> None:
        """Increment counter value by 1"""
        if self._value_int is None:
            self.value_int = 1
        else:
            self.value_int = self._value_int + 1

    def parse(self, name: str) -> bool:
        """Parse counter value from name string"""
        if self._pattern is None:
            self.initialize_cache()
            if self._pattern is None:
                return False

        match = self._pattern.search(name)
        if match:
            extracted_value = match.group(self.id)
            self._value = extracted_value  # 文字列値を直接設定

            try:
                self._value_int = self._parse_value(extracted_value)
                self.forward = match.string[: match.start(self.id)]
                self.backward = match.string[match.end(self.id) :]
                return True
            except ValueError:
                log.error(f"Failed to parse counter value: {extracted_value}")
                self._value_int = None

        return False

    def _parse_value(self, value_str: str) -> int:
        """Parse string value to integer - to be overridden by specific counter types"""
        return int(value_str)

    def take_over_counter(self, other: ICounter, force: bool = False) -> None:
        """Take over counter from another counter
        Args:
            other: カウンターの値を奪う対象のカウンター
            force: 自分の値が存在する場合でも奪うかどうか
        """
        if other.value is None:
            return

        if not force and self.value is not None and self.value_int > 0:
            self.add(other.value_int)
            other.set_value(None)
            return

        self.set_value(other.value_int)
        other.set_value(None)
