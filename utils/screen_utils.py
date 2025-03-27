from contextlib import contextmanager
from typing import Any, Dict, Union, Self, Optional, Tuple, TypeVar, cast

__all__ = [
    'BlenderContextManager',
    'get_context_override',
]

import bpy
from bpy.types import Area, Context, Region, Screen, Window


T = TypeVar('T')


def resolve_window(identifier: Any, context: Context) -> Optional[Window]:
    """ウィンドウ識別子をWindowオブジェクトに解決します。
    
    Args:
        identifier: ウィンドウ識別子
        context: Blenderコンテキスト
        
    Returns:
        Window: 解決されたWindowオブジェクト、または None
    """
    if identifier is None:
        return None
        
    if isinstance(identifier, Window):
        return identifier
        
    if not isinstance(identifier, (int, str)) or not str(identifier).isdigit():
        return None
        
    try:
        idx = int(identifier)
        wm = context.window_manager
        if idx < 0:
            idx = len(wm.windows) + idx
        idx = max(0, min(idx, len(wm.windows) - 1))
        return wm.windows[idx]
    except (ValueError, IndexError):
        return None


def resolve_screen(identifier: Any) -> Optional[Screen]:
    """スクリーン識別子をScreenオブジェクトに解決します。
    
    Args:
        identifier: スクリーン識別子
        
    Returns:
        Screen: 解決されたScreenオブジェクト、または None
    """
    if identifier is None:
        return None
        
    if isinstance(identifier, Screen):
        return identifier
        
    if isinstance(identifier, str):
        return bpy.data.screens.get(identifier)
        
    return None


def resolve_area(identifier: Any, screen: Screen) -> Optional[Area]:
    """エリア識別子をAreaオブジェクトに解決します。
    
    Args:
        identifier: エリア識別子
        screen: 親スクリーン
        
    Returns:
        Area: 解決されたAreaオブジェクト、または None
    """
    if identifier is None:
        return None
        
    if isinstance(identifier, Area):
        return identifier
        
    if isinstance(identifier, str):
        return next((ar for ar in screen.areas if ar.type == identifier), None)
        
    return None


def resolve_region(identifier: Any, area: Area) -> Optional[Region]:
    """リージョン識別子をRegionオブジェクトに解決します。
    
    Args:
        identifier: リージョン識別子
        area: 親エリア
        
    Returns:
        Region: 解決されたRegionオブジェクト、または None
    """
    if identifier is None or area is None:
        return None
        
    if isinstance(identifier, Region):
        return identifier
        
    if isinstance(identifier, (int, str)) and str(identifier).isdigit():
        try:
            idx = int(identifier)
            if idx < 0:
                idx = len(area.regions) + idx
            if 0 <= idx < len(area.regions):
                return area.regions[idx]
        except (ValueError, IndexError):
            return None
            
    if isinstance(identifier, str):
        return next((reg for reg in area.regions if reg.type == identifier), None)
        
    return None


def resolve_context_args(context: Context, **kwargs) -> Dict[str, Any]:
    """コンテキスト引数の識別子を解決します。
    
    Args:
        context: Blenderコンテキスト
        **kwargs: 解決する引数（window, screen, area, region）
        
    Returns:
        Dict[str, Any]: 解決された引数の辞書
    """
    result = {}
    
    # 特殊なキーを処理
    window_id = kwargs.pop('window', None)
    screen_id = kwargs.pop('screen', None)
    area_id = kwargs.pop('area', None)
    region_id = kwargs.pop('region', None)
    
    # 基本的なコンテキスト
    window = context.window
    screen = context.screen
    area = context.area
    region = context.region
    
    # 要素を順番に解決
    if window_id is not None:
        window = resolve_window(window_id, context)
        
    if window:
        result["window"] = window
        
    if screen_id is not None:
        screen = resolve_screen(screen_id)
        
    if screen:
        result["screen"] = screen
        
    if area_id is not None and screen:
        area = resolve_area(area_id, screen)
        
    if area:
        result["area"] = area
        
    if region_id is not None and area:
        region = resolve_region(region_id, area)
        
    if region:
        result["region"] = region
        
    # 残りの引数を追加
    result.update(kwargs)
    
    return result


class BlenderContextManager:
    """Blenderのコンテキスト管理を行うクラス。
    
    ウィンドウ、スクリーン、エリア、リージョンの階層構造を管理し、
    メソッドチェーンまたは直接指定の両方の方法で使用できます。
    
    階層構造:
    Window -> Screen -> Area -> Region
    
    使用例:
        # 基本的な使用方法
        with BlenderContextManager(context).find_area("VIEW_3D").temp_override():
            bpy.ops.view3d.some_operator()
            
        # 追加の引数が必要な場合
        with BlenderContextManager(context).find_area("VIEW_3D").add_kwargs(mode='EDIT').temp_override():
            bpy.ops.mesh.select_all()
            
        # 複数のエリアを指定する場合
        with BlenderContextManager(context).find_screen("Animation").find_area("GRAPH_EDITOR").temp_override():
            bpy.ops.graph.some_operator()
            
        # 直接指定での使用（シンプルな場合のみ）
        with BlenderContextManager(context).temp_override(area="VIEW_3D", mode='EDIT'):
            bpy.ops.mesh.select_all()
    """
    
    def __init__(self, context: Context = None):
        self.context = context or bpy.context
        self.window: Window = self.context.window
        self.screen: Screen = self.context.screen
        self.area: Area = self.context.area
        self.region: Region = self.context.region
        self._kwargs: Dict[str, Any] = {}
    
    def find_window(self, identifier: Union[int, Window, None]) -> Self:
        """指定されたウィンドウを探します。
        
        Args:
            identifier: ウィンドウの識別子。整数のインデックス、Windowオブジェクト、またはNone。
                       負の値の場合は後ろから数えます。
            
        Returns:
            self: メソッドチェーン用
            
        Raises:
            ValueError: ウィンドウが見つからない場合
        """
        if identifier is None:
            return self
            
        window = resolve_window(identifier, self.context)
        if window is None:
            raise ValueError(f"Window identifier not valid or not found: {identifier}")
            
        self.window = window
        return self
    
    def find_screen(self, identifier: Union[str, Screen, None]) -> Self:
        """指定されたスクリーンを探します。
        
        Args:
            identifier: スクリーンの識別子。名前、Screenオブジェクト、またはNone。
            
        Returns:
            self: メソッドチェーン用
            
        Raises:
            ValueError: スクリーンが見つからない場合
        """
        if identifier is None:
            return self
            
        screen = resolve_screen(identifier)
        if screen is None:
            raise ValueError(f"Screen identifier not valid or not found: {identifier}")
            
        self.screen = screen
        return self
    
    def find_area(self, identifier: Union[str, Area, None]) -> Self:
        """指定されたエリアを探します。
        
        Args:
            identifier: エリアの識別子。タイプ名、Areaオブジェクト、またはNone。
            
        Returns:
            self: メソッドチェーン用
            
        Raises:
            ValueError: エリアが見つからない場合
        """
        if identifier is None:
            return self
            
        area = resolve_area(identifier, self.screen)
        if area is None:
            raise ValueError(f"Area identifier not valid or not found: {identifier}")
            
        self.area = area
        return self
    
    def find_region(self, identifier: Union[str, int, Region, None]) -> Self:
        """指定されたリージョンを探します。
        
        Args:
            identifier: リージョンの識別子。タイプ名、整数のインデックス、Regionオブジェクト、またはNone。
                       インデックスの場合、負の値は後ろから数えます。
            
        Returns:
            self: メソッドチェーン用
            
        Raises:
            ValueError: リージョンが見つからない場合
        """
        if identifier is None:
            return self
            
        if self.area is None:
            raise ValueError("Area must be selected before finding a region")
            
        region = resolve_region(identifier, self.area)
        if region is None:
            raise ValueError(f"Region identifier not valid or not found: {identifier}")
            
        self.region = region
        return self
        
    def add_kwargs(self, **kwargs) -> Self:
        """追加のオーバーライド引数を設定します。
        
        Args:
            **kwargs: 追加のオーバーライド引数
            
        Returns:
            self: メソッドチェーン用
            
        Example:
            context_manager.find_area("VIEW_3D").add_kwargs(mode='EDIT').temp_override()
        """
        self._kwargs.update(kwargs)
        return self
    
    def get_override_args(self) -> Dict[str, Any]:
        """現在のコンテキスト状態に基づいてオーバーライド引数を取得します。
        
        Returns:
            Dict[str, Any]: オーバーライド引数の辞書
        """
        result = {}
        
        # 現在のコンテキスト状態を追加（Noneでない場合のみ）
        if self.window is not None:
            result["window"] = self.window
        if self.screen is not None:
            result["screen"] = self.screen
        if self.area is not None:
            result["area"] = self.area
        if self.region is not None:
            result["region"] = self.region
        
        # メソッドチェーンで追加された引数を適用
        if self._kwargs:
            result.update(self._kwargs)
            
        return result
    
    @contextmanager
    def temp_override(self, **kwargs):
        """コンテキストの一時的なオーバーライドを提供します。
        
        メソッドチェーンで設定された状態と、引数として渡された識別子を組み合わせます。
        
        Args:
            **kwargs: 追加のオーバーライド引数。特別なキー:
                window: ウィンドウ識別子
                screen: スクリーン識別子
                area: エリア識別子
                region: リージョン識別子
            
        Yields:
            Context: オーバーライドされたコンテキスト
            
        Example:
            # 直接指定
            with BlenderContextManager().temp_override(area="VIEW_3D", mode='EDIT'):
                bpy.ops.mesh.select_all()
                
            # メソッドチェーン
            with BlenderContextManager().find_area("VIEW_3D").add_kwargs(mode='EDIT').temp_override():
                bpy.ops.mesh.select_all()
        """
        # メソッドチェーンによる状態を取得
        override_args = self.get_override_args()
        
        # 特殊なキーを処理（window, screen, area, region）
        special_keys = {}
        for key in ['window', 'screen', 'area', 'region']:
            if key in kwargs:
                special_keys[key] = kwargs.pop(key)
        
        # 特殊キーの解決が必要な場合
        if special_keys:
            # 特殊キーを解決
            resolved = resolve_context_args(self.context, **special_keys)
            override_args.update(resolved)
        
        # 残りの引数を追加
        if kwargs:
            override_args.update(kwargs)
        
        # オーバーライドを適用
        with self.context.temp_override(**override_args) as override:
            yield override


# ショートカット関数
def get_context_override(context: Context = None, **kwargs) -> Dict[str, Any]:
    """便利なショートカット関数でコンテキストオーバーライド辞書を取得します。
    
    Args:
        context: Blenderコンテキスト（Noneの場合はbpy.contextを使用）
        **kwargs: オーバーライド引数
        
    Returns:
        Dict[str, Any]: オーバーライド引数の辞書
    
    Example:
        override = get_context_override(area="VIEW_3D")
        bpy.ops.view3d.some_operator(override)
    """
    context = context or bpy.context
    return resolve_context_args(context, **kwargs)
