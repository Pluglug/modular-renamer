アーキテクチャ概要
==================


.. mermaid::
    :caption: リネーム処理フロー

    sequenceDiagram
        participant ユーザー
        participant RenameService
        participant NamingPattern
        participant ElementRegistry
        participant BaseElement
        participant CounterElement
        participant ConflictResolver
        participant NamespaceManager
        
        ユーザー->>RenameService: リネーム要求
        RenameService->>NamingPattern: パターン取得
        NamingPattern->>ElementRegistry: 要素生成
        
        ElementRegistry->>BaseElement: テキスト要素生成
        BaseElement-->>ElementRegistry: 要素返却
        
        ElementRegistry->>CounterElement: カウンター要素生成
        CounterElement-->>ElementRegistry: 要素返却
        
        ElementRegistry-->>NamingPattern: 全要素返却
        NamingPattern-->>RenameService: 提案名生成
        
        RenameService->>ConflictResolver: 重複チェック依頼
        ConflictResolver->>NamespaceManager: 名前空間取得
        NamespaceManager-->>ConflictResolver: 名前空間返却
        
        alt 重複あり
            ConflictResolver->>CounterElement: カウンター値更新
            CounterElement->>CounterElement: increment()
            CounterElement-->>ConflictResolver: 新しい値
            
            loop 重複が解消されるまで
                ConflictResolver->>NamespaceManager: 重複チェック
                NamespaceManager-->>ConflictResolver: 結果
                
                opt まだ重複している場合
                    ConflictResolver->>CounterElement: 再度increment()
                    CounterElement-->>ConflictResolver: 新しい値
                end
            end
            
            ConflictResolver-->>RenameService: 解決済み名前
        else 重複なし
            ConflictResolver-->>RenameService: 提案名をそのまま返却
        end
        
        RenameService-->>ユーザー: 最終結果表示


.. mermaid::
    :caption: コレクターおよび名前空間のクラス図

    sequenceDiagram
        participant ユーザー
        participant RenameService
        participant TargetCollector
        participant RenameTarget
        participant ConflictResolver
        participant NamespaceManager
        participant Namespace
        
        ユーザー->>RenameService: リネーム要求（対象選択）
        RenameService->>TargetCollector: ターゲット収集依頼
        
        TargetCollector->>TargetCollector: 選択戦略に基づく収集
        TargetCollector-->>RenameService: RenameTarget配列返却
        
        loop 各ターゲットについて
            RenameService->>RenameTarget: 現在の名前取得
            RenameTarget-->>RenameService: 名前返却
            
            RenameService->>RenameService: 提案名生成（前の図の処理）
            
            RenameService->>ConflictResolver: 重複チェック
            ConflictResolver->>RenameTarget: 名前空間キー取得
            RenameTarget-->>ConflictResolver: キー返却（例：オブジェクト種別）
            
            ConflictResolver->>NamespaceManager: 名前空間取得
            NamespaceManager->>Namespace: 特定のNamespace取得
            Namespace-->>NamespaceManager: Namespace返却
            NamespaceManager-->>ConflictResolver: Namespace返却
            
            ConflictResolver->>Namespace: 名前の重複チェック
            Namespace-->>ConflictResolver: 重複状態返却
            
            alt 重複解決後
                RenameService->>RenameTarget: 名前変更実行
                RenameTarget->>Namespace: 名前空間更新
                Namespace-->>RenameTarget: 更新完了
                RenameTarget-->>RenameService: 変更完了
            end
        end
        
        RenameService-->>ユーザー: 全ターゲットのリネーム結果



.. mermaid::
    :config: {"flowchart": {"nodeSpacing": 50, "rankSpacing": 70}}
    :caption: システムアーキテクチャ図
    :zoom:

    classDiagram
        namespace core_elements {
            class ElementConfig {
                +type: str
                +id: str
                +order: int
                +enabled: bool
                +separator: str
                +validate(obj: Any) Optional[str]
                +is_valid() bool
                +from_dict(data: dict) ElementConfig
            }
            class INameElement {
                <<interface>>
                +element_type: str
                +id: str
                +order: int
                +enabled: bool
                +separator: str
                +value: Any
                +parse(name: str) bool
                +render() tuple[str, str]
                +set_value(value: Any) void
                +standby() void
                +initialize_cache() void
            }
            class BaseElement {
                <<abstract>>
                #_value: Any
                #_pattern: Pattern
                +cache_invalidated: bool
                +parse(name: str) bool
                +render() tuple[str, str]
                +set_value(value: Any) void
                +standby() void
                +initialize_cache() void
                #_build_pattern() str
                #generate_random_value() str
            }
            class ICounter {
                <<interface>>
                +value_int: int
                +increment() void
                +format_value(value: int) str
                +gen_proposed_name(value: int) str
            }
            class BaseCounter {
                <<abstract>>
                #_value_int: int
                +forward: str
                +backward: str
                +increment() void
                +format_value(value: int) str
                #_parse_value(value_str: str) int
            }
        }
        namespace elements {
            class TextElement {
                +items: List[str]
                +parse(name: str) bool
                +render() tuple[str, str]
                +set_value(value: Any) void
                #_build_pattern() str
                #generate_random_value() tuple[str, str]
            }
            class PositionElement {
                +xaxis_values: List[str]
                +yaxis_values: List[str]
                +zaxis_values: List[str]
                +position_values: List[str]
                +parse(name: str) bool
                +render() tuple[str, str]
                #_build_pattern() str
                #generate_random_value() tuple[str, str]
            }
            class NumericCounter {
                +digits: int
                +format_value(value: int) str
                +gen_proposed_name(value: int) str
                #_build_pattern() str
                #generate_random_value() tuple[str, str]
            }
            class BlenderCounter {
                +digits: int
                +format_value(value: int) str
                +gen_proposed_name(value: int) str
                #_build_pattern() str
                #_parse_value(value_str: str) int
                #generate_random_value() tuple[str, str]
            }
            class AlphabeticCounter {
                +uppercase: bool
                +format_value(value: int) str
                +gen_proposed_name(value: int) str
                #_build_pattern() str
                #_parse_value(value_str: str) int
                #generate_random_value() tuple[str, str]
            }
        }
        namespace core {
            class ElementRegistry {
                -_element_types: Dict[str, Type]
                -_instance: ElementRegistry
                -_is_initialized: bool
                +get_instance() ElementRegistry
                +reset_instance() void
                +register_element_type(type: str, class: Type) void
                +get_element_type(type_name: str) Optional[Type[INameElement]]
                +create_element(element_config: ElementConfig) INameElement
                +get_registered_types() List[str]
                -_initialize_default_elements() void
            }
            class NamingPattern {
                +name: str
                +target_type: str
                +elements: List[INameElement]
                +parse_name(name: str) void
                +update_elements(updates: Dict) void
                +render_name() str
                +validate() List[str]
                +get_element_by_id(element_id: str) INameElement
                +gen_test_names(random: bool, num_cases: int) List[str]
                -_load_elements(config: List, element_registry: ElementRegistry) void
                -_notify_elements_changed() void
            }
            class PatternRegistry {
                -patterns: Dict[str, Dict[str, NamingPattern]]
                +register_pattern(pattern: NamingPattern) void
                +get_pattern(type: str, name: str) NamingPattern
                +get_patterns_for_type(type: str) List[NamingPattern]
                +load_from_file(path: str) void
                +save_to_file(path: str) void
            }
            class IRenameTarget {
                <<interface>>
                +get_name() str
                +set_name(name: str) void
                +get_namespace_key() Any
                +target_type: str
                +blender_object: Any
            }
            class INamespace {
                <<interface>>
                +contains(name: str) bool
                +add(name: str) void
                +remove(name: str) void
                +update(old: str, new: str) void
            }
            class NamespaceBase {
                <<abstract>>
                #names: Set[str]
                +contains(name: str) bool
                +add(name: str) void
                +remove(name: str) void
                +update(old: str, new: str) void
                #_initialize() void
            }
            class NamespaceManager {
                -namespaces: Dict[Any, INamespace]
                -_namespace_factories: Dict[str, Callable]
                +register_namespace_type(type: str, factory: Callable) void
                +get_namespace(target: IRenameTarget) INamespace
            }
            class CollectionStrategy {
                <<interface>>
                +collect(context: Context) List[IRenameTarget]
            }
            class TargetCollector {
                -strategies: Dict[str, CollectionStrategy]
                +register_strategy(type: str, strategy: CollectionStrategy) void
                +collect(type: str, context: Context) List[IRenameTarget]
            }
            class ConflictResolver {
                -namespace_manager: NamespaceManager
                -resolved_conflicts: List[Dict]
                +STRATEGY_COUNTER: str
                +STRATEGY_FORCE: str
                +resolve(target: IRenameTarget, name: str, strategy: str) str
                -_resolve_with_counter(target: IRenameTarget, name: str, namespace: INamespace) str
                -_resolve_with_force(target: IRenameTarget, name: str, namespace: INamespace) str
                -_find_conflicting_targets(target: IRenameTarget, name: str) List[IRenameTarget]
            }
            class RenameContext {
                +target: IRenameTarget
                +pattern: NamingPattern
                +original_name: str
                +proposed_name: str
                +final_name: str
                +conflict_resolution: Any
            }
            class RenameService {
                -pattern_registry: PatternRegistry
                -namespace_manager: NamespaceManager
                -conflict_resolver: ConflictResolver
                +prepare(target: IRenameTarget, pattern: str) RenameContext
                +update_elements(context: RenameContext, updates: Dict) RenameContext
                +execute(context: RenameContext, strategy: str) bool
                +batch_rename(targets: List[IRenameTarget], pattern: str, updates: Dict, strategy: str) List[RenameContext]
            }
        }
        namespace targets {
            class ObjectRenameTarget {
                -obj: Object
                +get_name() str
                +set_name(name: str) void
                +get_namespace_key() Any
                +target_type: str
                +blender_object: Object
            }
            class PoseBoneRenameTarget {
                -pose_bone: PoseBone
                +get_name() str
                +set_name(name: str) void
                +get_namespace_key() Any
                +target_type: str
                +blender_object: PoseBone
            }
            class MaterialRenameTarget {
                -material: Material
                +get_name() str
                +set_name(name: str) void
                +get_namespace_key() Any
                +target_type: str
                +blender_object: Material
            }
            class ObjectNamespace {
                -scene: Scene
                -names: Set[str]
                +contains(name: str) bool
                +add(name: str) void
                +remove(name: str) void
                +update(old: str, new: str) void
                -_initialize() void
            }
            class BoneNamespace {
                -armature: Armature
                -names: Set[str]
                +contains(name: str) bool
                +add(name: str) void
                +remove(name: str) void
                +update(old: str, new: str) void
                -_initialize() void
            }
            class SelectedObjectsStrategy {
                +collect(context: Context) List[IRenameTarget]
            }
            class SelectedPoseBonesStrategy {
                +collect(context: Context) List[IRenameTarget]
            }
            class ModifiersStrategy {
                -obj: Object
                +collect(context: Context) List[IRenameTarget]
            }
        }
        namespace ui {
            class RenameSettings {
                +default_target_type: str
                +default_conflict_strategy: str
                +show_warnings: bool
                +auto_save_patterns: bool
            }
            class RenameProperties {
                +mode: str
                +target_type: str
                +pattern: str
                +conflict_strategy: str
                +patterns: List
                +active_pattern_index: int
                +active_element_index: int
            }
            class RENAME_PT_main_panel {
                +draw(context: Context) void
                -draw_rename_mode(context: Context, layout: UILayout) void
                -draw_edit_mode(context: Context, layout: UILayout) void
                -draw_element_actions(context: Context, layout: UILayout, element: INameElement) void
            }
            class RENAME_OT_execute {
                +execute(context: Context) dict
                +invoke(context: Context, event: Event) dict
            }
            class RENAME_UL_patterns {
                +draw_item(context: Context, layout: UILayout, data, item, icon, active_data, active_propname, index: int) void
            }
        }
        namespace utils {
            class ModularLogger {
                +log_level: int
                +log_to_file: bool
                +info(message: str) void
                +warning(message: str) void
                +error(message: str) void
                +debug(message: str) void
            }
            class ConfigManager {
                +export_settings(path: str) bool
                +import_settings(path: str) bool
                +get_user_presets_dir() str
                +get_user_patterns_dir() str
                +get_export_dir() str
            }
        }
        INameElement <|-- BaseElement
        BaseElement <|-- TextElement
        BaseElement <|-- PositionElement
        BaseElement <|-- BaseCounter
        ICounter <|-- BaseCounter
        BaseCounter <|-- NumericCounter
        BaseCounter <|-- BlenderCounter
        BaseCounter <|-- AlphabeticCounter
        IRenameTarget <|-- ObjectRenameTarget
        IRenameTarget <|-- PoseBoneRenameTarget
        IRenameTarget <|-- MaterialRenameTarget
        INamespace <|-- NamespaceBase
        NamespaceBase <|-- ObjectNamespace
        NamespaceBase <|-- BoneNamespace
        CollectionStrategy <|-- SelectedObjectsStrategy
        CollectionStrategy <|-- SelectedPoseBonesStrategy
        CollectionStrategy <|-- ModifiersStrategy
        ElementRegistry --> INameElement : creates >
        ElementRegistry --> ElementConfig : uses >
        NamingPattern --> INameElement : contains 1..*
        NamingPattern --> ElementConfig : configures >
        PatternRegistry --> NamingPattern : manages *
        NamespaceManager --> INamespace : manages *
        TargetCollector --> CollectionStrategy : uses *
        TargetCollector --> IRenameTarget : collects *
        ConflictResolver --> NamespaceManager : uses 1
        ConflictResolver --> IRenameTarget : resolves for 1
        RenameContext --> IRenameTarget : references 1
        RenameContext --> NamingPattern : uses 1
        RenameService --> PatternRegistry : uses 1
        RenameService --> NamespaceManager : uses 1
        RenameService --> ConflictResolver : uses 1
        RenameService --> RenameContext : creates >
        RENAME_PT_main_panel --> RenameProperties : uses 1
        RENAME_OT_execute --> RenameService : uses 1
        RENAME_UL_patterns --> PatternRegistry : displays 1
        NamingPattern "1" o-- "*" INameElement : contains
        PatternRegistry "1" o-- "*" NamingPattern : registers
        NamespaceManager "1" o-- "*" INamespace : manages
        TargetCollector "1" o-- "*" CollectionStrategy : uses
        RenameService "1" --> "1" NamespaceManager : depends on
        RenameService "1" --> "1" PatternRegistry : depends on
        RenameService "1" --> "1" ConflictResolver : depends on


.. なんかmermaidディレクティブがひとつだけだとZOOMが効かないので、
   2つ目を追加してみた。