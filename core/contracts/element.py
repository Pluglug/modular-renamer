import re
from abc import ABC, abstractmethod
from typing import Any, ClassVar, Dict, Optional, Set, Tuple

from ...utils.logging import get_logger
from ...utils.strings_utils import is_pascal_case, to_snake_case

log = get_logger(__name__)


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
        self.type: str = type
        self.id: str = id
        self.order: int = order
        self.enabled: bool = enabled
        self.separator: str = separator

        # Store any additional properties
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __getattr__(self, name: str) -> Any:
        """
        動的に追加された属性にアクセスするためのフォールバック
        """
        if name in self.__dict__:
            return self.__dict__[name]
        raise AttributeError(f"'ElementConfig' object has no attribute '{name}'")


class INameElement(ABC):
    """
    名前要素のインターフェース
    """

    element_type: ClassVar[str]
    config_fields: ClassVar[Dict[str, Any]]

    @classmethod
    @abstractmethod
    def validate_config(cls, config: ElementConfig) -> Optional[str]:
        pass

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
    def value(self) -> str | None:
        pass

    @abstractmethod
    def parse(self, name: str) -> bool:
        """
        指定した文字列から自身の値を抽出する
        """
        pass

    @abstractmethod
    def render(self) -> Tuple[str, str] | None:
        """
        (separator, value) の組として値をレンダリングする
        """
        pass

    @abstractmethod
    def set_value(self, new_value: str | None) -> None:
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

    config_fields: ClassVar[Dict[str, Any]] = {
        "type": str,
        "id": str,
        "order": int,
        "enabled": bool,
        "separator": str,
    }

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

    @classmethod
    def validate_config(cls, config: ElementConfig) -> Optional[str]:
        """
        設定のバリデーション

        Args:
            config: 検証する設定

        Returns:
            str: エラーメッセージ。問題なければNone
        """
        # ElementConfigの型チェック
        if not isinstance(config, ElementConfig):
            return "要素設定がElementConfig型ではありません"

        # 必須フィールドの存在と型チェック
        for field_name, field_type in cls.config_fields.items():
            if not hasattr(config, field_name):
                return f"必須フィールド '{field_name}' がありません"

            value = getattr(config, field_name)
            if not isinstance(value, field_type):
                return f"フィールド '{field_name}' の型が不正です: expected {field_type}, got {type(value)}"

        return None

    @classmethod
    def get_config_names(cls) -> Set[str]:
        """
        設定フィールド名のセットを返す
        """
        return set(cls.config_fields.keys())

    def __init__(self, element_config: ElementConfig):
        self._id = element_config.id
        self._order = element_config.order
        self._enabled = element_config.enabled
        self._separator = element_config.separator

        self._value: str | None = None
        self._pattern: re.Pattern[str] | None = None
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
    def value(self) -> str | None:
        return self._value

    def set_value(self, new_value: str | None) -> None:
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
            if self._pattern is None:
                return False
        match = self._pattern.search(name)
        if match:
            self._value = match.group(self.id)
            return True
        return False

    def render(self) -> Tuple[str, str] | None:
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
    def generate_random_value(self) -> Tuple[str, str]:
        """Generate a random value for this element (for testing)"""
        pass
