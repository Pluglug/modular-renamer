"""
名前要素の基本インターフェイスおよび基本実装
旧 NamingElementProcessor
"""

import re
from abc import ABC, abstractmethod
from typing import Any, Tuple, Optional

from ..utils import logging
from ..utils.strings_utils import is_pascal_case, to_snake_case

log = logging.get_logger(__name__)


class ElementConfig:
    """
    Data structure for element configuration
    """

    def __init__(
        self,
        type: str,
        id: str,
        order: int,
        enabled: bool = True,
        separator: str = "_",
        **kwargs,
    ):
        self.type = type
        self.id = id
        self.order = order
        self.enabled = enabled
        self.separator = separator

        # Store any additional properties
        for key, value in kwargs.items():
            setattr(self, key, value)

    @classmethod
    def validate(cls, obj: Any) -> Optional[str]:
        """
        ElementConfigの検証
        """
        if not isinstance(obj, cls):
            return "要素設定がElementConfig型ではありません"

        if not obj.type and not isinstance(obj.type, str):
            return "要素設定にtypeがありません"

        if not obj.id or not isinstance(obj.id, str):
            return "要素設定にidがありません"

        if not hasattr(obj, "order") or not isinstance(obj.order, int):
            return "要素設定にorderがありません"

        if not hasattr(obj, "enabled") or not isinstance(obj.enabled, bool):
            return "要素設定にenabledがありません"

        if not obj.separator and not isinstance(obj.separator, str):
            return "要素設定にseparatorがありません"

        return None

    def is_valid(self) -> bool:
        """
        ElementConfigが有効かどうかを返す
        """
        return self.validate(self) is None

    @classmethod
    def from_dict(cls, data: dict) -> "ElementConfig":
        """
        dictからElementConfigを生成する
        """
        return cls(**data)


class INameElement(ABC):
    """
    名前要素のインターフェース
    """

    @classmethod
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if not hasattr(cls, "element_type"):
            name = cls.__name__.replace("Element", "")
            if is_pascal_case(name):
                cls.element_type = to_snake_case(name)
            else:
                log.warning(f"PascalCaseではない要素名: {name}")
                cls.element_type = name.lower()

    @property
    @abstractmethod
    def id(self) -> str:
        pass

    @property
    @abstractmethod
    def order(self) -> int:
        pass

    @property
    @abstractmethod
    def enabled(self) -> bool:
        pass

    @property
    @abstractmethod
    def separator(self) -> str:
        pass

    @property
    @abstractmethod
    def value(self) -> str:
        pass

    @abstractmethod
    def parse(self, name: str) -> bool:
        """
        指定した文字列から自身の値を抽出する
        """
        pass

    @abstractmethod
    def render(self) -> Tuple[str, str]:
        """
        (separator, value) の組として値をレンダリングする
        """
        pass

    @abstractmethod
    def set_value(self, new_value: Any) -> None:
        """
        要素の値を設定する
        """
        pass

    @abstractmethod
    def standby(self) -> None:
        """
        オペレーター実行前の初期化処理。解析用の状態をリセットする
        """
        pass

    @abstractmethod
    def initialize_cache(self) -> None:
        """
        ユーザー設定完了時に一度だけ呼ばれ、正規表現のコンパイルなどのキャッシュ処理を行う
        """
        pass


class BaseElement(INameElement, ABC):
    """
    INameElement の基本実装。
    ユーザー設定完了時にキャッシュ（コンパイル済み正規表現）を生成し、
    オペレーター実行時には standby により値だけをリセットする。
    """

    def __init__(self, element_config: ElementConfig):
        self._id = element_config.get("id")
        self._order = element_config.get("order")
        self._enabled = element_config.get("enabled")
        self._separator = element_config.get("separator")

        self._value = None
        self._pattern = None
        self.cache_invalidated = True

    @property
    def id(self) -> str:
        return self._id

    @property
    def order(self) -> int:
        return self._order

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def separator(self) -> str:
        return self._separator

    @property
    def value(self) -> str:
        return self._value

    def set_value(self, new_value: Any) -> None:
        if new_value is not None:
            try:
                self._value = str(new_value)
            except ValueError:
                log.error(f"Value '{new_value}' cannot be converted to string.")
        else:
            self._value = None

    def initialize_cache(self) -> None:
        """
        ユーザー設定完了後に呼ばれ、正規表現パターンをコンパイルする。
        この処理は1度だけ行われ、以降はキャッシュ済みのパターンを利用する。
        """
        if self.cache_invalidated or self._pattern is None:
            pattern_str = self._build_pattern()
            self._pattern = re.compile(pattern_str)
            self.cache_invalidated = False

    def standby(self) -> None:
        """
        オペレーター実行前に呼ばれ、解析のための状態（値）をリセットする。
        キャッシュ済みの正規表現パターンはそのまま利用する。
        """
        self._value = None

    def parse(self, name: str) -> bool:
        """
        キャッシュ済みのパターンを用いて名前文字列から値を抽出する。
        """
        # 初期化処理が呼ばれていなかった場合の保険として
        if self._pattern is None:
            log.debug(f"Cache is not initialized for {self.id}. Initializing cache...")
            self.initialize_cache()
        match = self._pattern.search(name)
        if match:
            self._value = match.group(self.id)
            return True
        return False

    def render(self) -> Tuple[str, str]:
        """
        要素が有効かつ値が存在する場合、(separator, value) の組を返す
        """
        if self.enabled and self._value:
            return (self.separator, self._value)
        return None

    @abstractmethod
    def _build_pattern(self) -> str:
        """
        各要素固有の正規表現パターンを構築する。
        このメソッドはサブクラスで実装する。
        """
        pass

    @abstractmethod
    def generate_random_value(self) -> str:
        """Generate a random value for this element (for testing)"""
        pass


class ICounter(ABC):
    """Interface for all counter types"""

    @property
    @abstractmethod
    def value_int(self) -> int:
        """Get counter's integer value"""
        pass

    @value_int.setter
    @abstractmethod
    def value_int(self, value: int) -> None:
        """Set counter's integer value"""
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


class BaseCounter(BaseElement, ICounter):
    """Base implementation for all counters"""

    def __init__(self, element_config: ElementConfig):
        super().__init__(element_config)
        self._value_int = None
        self.forward = None
        self.backward = None

    @property
    def value_int(self) -> int:
        return self._value_int

    @value_int.setter
    def value_int(self, value: int) -> None:
        if value is not None:
            self._value_int = value
            self._value = self.format_value(value)
        else:
            self._value_int = None
            self._value = None

    def set_value(self, new_value: Any) -> None:
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
