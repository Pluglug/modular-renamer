アーキテクチャ概要
==================


.. mermaid::
    :caption: リネーム処理フロー

    sequenceDiagram
        participant User
        participant RenameService
        participant NamingPattern
        participant ElementRegistry
        
        User->>RenameService: リネーム要求
        RenameService->>NamingPattern: パターン取得
        NamingPattern->>ElementRegistry: 要素生成
        ElementRegistry-->>NamingPattern: 要素返却
        NamingPattern-->>RenameService: パターン適用
        RenameService-->>User: 結果を表示


.. mermaid::
    :config: {"flowchart": {"nodeSpacing": 50, "rankSpacing": 70}}
    :caption: システムアーキテクチャ図
    :zoom:

    classDiagram
        namespace core_elements {
            class INameElement {
                <<interface>>
                +id: str
                +order: int
                +enabled: bool
                +separator: str
                +value: Any
                +parse(name: str) bool
                +render() tuple[str, str]
                +set_value(value: Any) void
            }
            class BaseElement {
                <<abstract>>
                #_value: Any
                #_pattern: Pattern
                +id: str
                +order: int
                +enabled: bool
                +separator: str
                +parse(name: str) bool
                +render() tuple[str, str]
                +set_value(value: Any) void
                #_build_pattern() Pattern
            }
        }
        namespace elements {
            class TextElement {
                +items: List[str]
                +parse(name: str) bool
                +render() tuple[str, str]
                +set_value(value: Any) void
                #_build_pattern() Pattern
            }
            class CounterElement {
                +digits: int
                +parse(name: str) bool
                +render() tuple[str, str]
                +set_value(value: Any) void
                +increment() void
                #_build_pattern() Pattern
            }
            class PositionElement {
                +items: List[str]
                +parse(name: str) bool
                +render() tuple[str, str]
                +set_value(value: Any) void
                #_build_pattern() Pattern
            }
            class BlenderCounterElement {
                +parse(name: str) bool
                +render() tuple[str, str]
                +set_value(value: Any) void
                +transfer_to(counter: CounterElement) void
                #_build_pattern() Pattern
            }
        }
        namespace core {
            class ElementRegistry {
                -_element_types: Dict[str, Type]
                +register_element_type(type: str, class: Type) void
                +create_element(type: str, config: dict) INameElement
                +get_registered_types() List[str]
                +validate_elements_config(config: List) List[str]
            }
            class NamingPattern {
                +name: str
                +target_type: str
                +elements: List[INameElement]
                +parse_name(name: str) void
                +update_elements(updates: Dict) void
                +render_name() str
                +validate() List[str]
                -_load_elements(config: List) void
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
        BaseElement <|-- CounterElement
        BaseElement <|-- PositionElement
        BaseElement <|-- BlenderCounterElement
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
        NamingPattern --> INameElement : contains 1..*
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