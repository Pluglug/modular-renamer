アーキテクチャ概要
==================


.. mermaid::
    :caption: 順次処理型一括リネーム処理フロー
    :zoom:

    sequenceDiagram
        participant ユーザー
        participant RENAME_OT_execute
        participant RenameService
        participant TargetCollector
        participant RenameContext
        participant PatternRegistry
        participant NamingPattern
        participant ConflictResolver
        participant NamespaceCache
        
        ユーザー->>RENAME_OT_execute: リネーム実行操作
        RENAME_OT_execute->>RenameService: prepare_batch()
        
        RenameService->>PatternRegistry: パターン取得
        PatternRegistry-->>RenameService: NamingPattern返却
        
        RenameService->>TargetCollector: ターゲット収集
        TargetCollector->>TargetCollector: コンテキストに基づく収集
        TargetCollector-->>RenameService: ターゲットリスト返却
        
        RenameService->>RenameContext: 新しいバッチ操作作成
        RenameService-->>RENAME_OT_execute: バッチ操作返却
        
        RENAME_OT_execute->>RenameService: execute_batch()
        
        loop 各ターゲットについて
            RenameService->>NamingPattern: 提案名生成
            NamingPattern-->>RenameService: 提案名返却
            
            RenameService->>ConflictResolver: 重複チェック・解決依頼
            ConflictResolver->>NamespaceCache: 名前空間取得
            NamespaceCache-->>ConflictResolver: 名前空間返却
            
            opt 重複あり
                ConflictResolver->>NamingPattern: カウンター要素取得
                NamingPattern->>NamingPattern: カウンター要素をincrement()
                NamingPattern-->>ConflictResolver: 更新された名前返却
                
                loop 重複が解消されるまで
                    ConflictResolver->>NamespaceCache: 重複再チェック
                    NamespaceCache-->>ConflictResolver: 結果返却
                    
                    opt まだ重複している場合
                        ConflictResolver->>NamingPattern: カウンター要素を再度increment()
                        NamingPattern-->>ConflictResolver: 更新された名前返却
                    end
                end
            end
            
            ConflictResolver->>NamespaceCache: シミュレーション名前空間を即時更新
            NamespaceCache-->>ConflictResolver: 更新完了
            ConflictResolver-->>RenameService: 解決済み名前返却
            
            RenameService->>RenameService: リネーム結果を記録（実際のBlenderオブジェクトはまだ更新しない）
        end
        
        loop 名前適用処理
            RenameService->>IRenameTarget: 名前設定
            IRenameTarget-->>RenameService: 適用完了
            
            RenameService->>ConflictResolver: 実際の名前空間更新
            ConflictResolver->>NamespaceCache: 更新実行
            NamespaceCache-->>ConflictResolver: 更新完了
            ConflictResolver-->>RenameService: 更新完了
        end
        
        RenameService->>RenameContext: 結果を保存
        RenameService-->>RENAME_OT_execute: 実行結果返却
        RENAME_OT_execute-->>ユーザー: 完了通知


.. mermaid::
    :caption: 名前空間管理と競合解決フロー
    :zoom:

    sequenceDiagram
        participant RenameService
        participant ConflictResolver
        participant NamespaceCache
        participant Namespace
        participant IRenameTarget
        participant NamingPattern
        
        RenameService->>ConflictResolver: resolve_name_conflict(target, pattern, proposed_name, strategy)
        ConflictResolver->>IRenameTarget: 名前空間キー取得
        IRenameTarget-->>ConflictResolver: キー返却（例：オブジェクト種別）
        
        ConflictResolver->>NamespaceCache: 名前空間取得
        NamespaceCache->>Namespace: 特定のNamespace取得
        Namespace-->>NamespaceCache: Namespace返却
        NamespaceCache-->>ConflictResolver: Namespace返却
        
        ConflictResolver->>Namespace: 名前の重複チェック
        Namespace-->>ConflictResolver: 重複状態返却
        
        alt 重複あり
            alt 戦略 = COUNTER
                ConflictResolver->>NamingPattern: カウンター要素取得
                NamingPattern->>NamingPattern: increment()で名前更新
                NamingPattern-->>ConflictResolver: 更新名返却
                
                loop 重複が解消されるまで
                    ConflictResolver->>Namespace: 再度重複チェック
                    Namespace-->>ConflictResolver: 重複状態返却
                    
                    opt まだ重複している
                        ConflictResolver->>NamingPattern: 再度increment()
                        NamingPattern-->>ConflictResolver: 更新名返却
                    end
                end
            else 戦略 = FORCE
                Note over ConflictResolver: 重複を無視
            end
        end
        
        ConflictResolver->>NamespaceCache: シミュレーション名前空間を更新
        NamespaceCache->>Namespace: 更新（実際のオブジェクトはまだ変更なし）
        Namespace-->>NamespaceCache: 更新完了
        NamespaceCache-->>ConflictResolver: 完了
        
        ConflictResolver-->>RenameService: 解決済み名前返却
        
        Note over RenameService: すべてのターゲットの名前解決後
        
        RenameService->>ConflictResolver: apply_namespace_update(target, old_name, new_name)
        ConflictResolver->>NamespaceCache: 実際の名前空間更新
        NamespaceCache->>Namespace: 更新
        Namespace-->>NamespaceCache: 更新完了
        NamespaceCache-->>ConflictResolver: 完了
        ConflictResolver-->>RenameService: 更新完了


.. mermaid::
    :config: {"flowchart": {"nodeSpacing": 50, "rankSpacing": 70}}
    :caption: システムアーキテクチャ図（一括リネーム中心）
    :zoom:

    classDiagram
        direction TD
        %% 要素関連のコンポーネント
        namespace core_elements {
            class ElementConfig {
                +type: str
                +id: str
                +order: int
                +enabled: bool
                +separator: str
            }
            class INameElement {
                <<interface>>
                +element_type: ClassVar[str]
                +config_fields: ClassVar[Dict[str, Any]]
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
                +config_fields: ClassVar[Dict[str, Any]]
                +validate_config(config: ElementConfig) Optional[str]
                +get_config_names() Set[str]
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

        %% 具体的な要素
        namespace elements {
            class TextElement {
                +items: List[str]
                +config_fields: Dict[str, Any]
                +validate_config(config: ElementConfig) Optional[str]
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
                +config_fields: Dict[str, Any]
                +validate_config(config: ElementConfig) Optional[str]
                +parse(name: str) bool
                +render() tuple[str, str]
                #_build_pattern() str
                #generate_random_value() tuple[str, str]
            }
            class NumericCounter {
                +digits: int
                +config_fields: Dict[str, Any]
                +validate_config(config: ElementConfig) Optional[str]
                +format_value(value: int) str
                +gen_proposed_name(value: int) str
                #_build_pattern() str
                #generate_random_value() tuple[str, str]
            }
            class BlenderCounter {
                +digits: int
                +config_fields: Dict[str, Any]
                +validate_config(config: ElementConfig) Optional[str]
                +format_value(value: int) str
                +gen_proposed_name(value: int) str
                #_build_pattern() str
                #_parse_value(value_str: str) int
                #generate_random_value() tuple[str, str]
            }
            class AlphabeticCounter {
                +uppercase: bool
                +config_fields: Dict[str, Any]
                +validate_config(config: ElementConfig) Optional[str]
                +format_value(value: int) str
                +gen_proposed_name(value: int) str
                #_build_pattern() str
                #_parse_value(value_str: str) int
                #generate_random_value() tuple[str, str]
            }
        }

        %% ターゲットシステム
        namespace core {
            class IRenameTarget {
                <<interface>>
                +get_name() str
                +set_name(name: str) void
                +get_namespace_key() str
                +target_type: str
                +get_blender_object() Any
                +create_namespace(context: Context) INamespace
            }
            class INamespace {
                <<interface>>
                +contains(name: str) bool
                +add(name: str) void
                +remove(name: str) void
                +update(old: str, new: str) void
            }
            class Namespace {
                -_context: Context
                -_names: Set[str]
                -_initializer: Optional[Callable]
                +__init__(context: Context, initializer: Optional[Callable])
                +contains(name: str) bool
                +add(name: str) void
                +remove(name: str) void
                +update(old: str, new: str) void
                -_initialize() void
            }
            class NamespaceCache {
                -_context: Context
                -_namespaces: Dict[Any, INamespace]
                +__init__(context: Context)
                +get_namespace(target: IRenameTarget) INamespace
                +update_context(context: Context) void
                +clear() void
                +get_all_namespaces() List[INamespace]
            }
            class TargetCollection {
                -_context: Context
                -_targets: List[IRenameTarget]
                +__init__(context: Context)
                +collect_by_type(target_type: str) List[IRenameTarget]
                +collect_selected() List[IRenameTarget]
                +collect_all() List[IRenameTarget]
                +update_context(context: Context) void
            }
        }

        %% パターンシステム
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
                -_patterns: Dict[str, NamingPattern]
                +register_pattern(pattern: NamingPattern) void
                +get_pattern(name: str) Optional[NamingPattern]
                +get_all_patterns() List[NamingPattern]
                +remove_pattern(name: str) void
                +clear() void
            }
            class PatternConfigManager {
                -_element_registry: ElementRegistry
                -_pattern_registry: PatternRegistry
                +create_pattern(name: str, elements_data: List[Dict]) NamingPattern
                +load_from_file(path: str) void
                +save_to_file(file_path: str, pattern_name: str) void
                +save_all_patterns(file_path: str) void
                -_convert_to_element_config(element_data: Dict) ElementConfig
            }
        }

        %% リネームサービス
        namespace core {
            class ConflictResolver {
                -_namespace_cache: NamespaceCache
                +STRATEGY_COUNTER: str = "counter"
                +STRATEGY_FORCE: str = "force"
                +resolve_name_conflict(target: IRenameTarget, pattern: NamingPattern, proposed_name: str, strategy: str) str
                +apply_namespace_update(target: IRenameTarget, old_name: str, new_name: str) void
                -_get_namespace(target: IRenameTarget) Optional[INamespace]
                -_is_name_in_conflict(name: str, namespace: INamespace, target: IRenameTarget) bool
                -_resolve_with_counter(pattern: NamingPattern, name: str, namespace: INamespace) str
                -_resolve_with_force(name: str) str
                -_find_conflicting_targets(target: IRenameTarget, name: str) List[IRenameTarget]
            }
            class RenameResult {
                +target: IRenameTarget
                +original_name: str
                +proposed_name: str
                +final_name: str
                +success: bool
                +message: str
            }
            class RenameContext {
                +targets: List[IRenameTarget]
                +pattern: NamingPattern
                +element_updates: Dict
                +strategy: str
                +results: List[RenameResult]
                +pending_results: Dict[str, RenameResult]
                +has_conflicts: bool
                +get_result_summary() str
            }
            class RenameService {
                -_pattern_registry: PatternRegistry
                -_target_collection: TargetCollection
                -_namespace_cache: NamespaceCache
                -_conflict_resolver: ConflictResolver
                +__init__(context: Context)
                +update_context(context: Context) void
                +prepare_batch(target_type: str, pattern_name: str) RenameContext
                +execute_batch(r_ctx: RenameContext) List[RenameResult]
            }
        }

        %% 具体的な実装
        namespace targets {
            class BaseRenameTarget {
                <<abstract>>
                #_blender_obj: Any
                +get_name() str
                +set_name(name: str) void
                +get_blender_object() Any
                +create_namespace(context: Context) INamespace
            }
            class ObjectRenameTarget {
                +target_type: str = "OBJECT"
                +get_namespace_key() str
                +create_namespace(context: Context) INamespace
            }
            class PoseBoneRenameTarget {
                +target_type: str = "POSE_BONE"
                +get_namespace_key() str
                +create_namespace(context: Context) INamespace
            }
            class MaterialRenameTarget {
                +target_type: str = "MATERIAL"
                +get_namespace_key() str
                +create_namespace(context: Context) INamespace
            }
        }

        %% UI
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

        %% ユーティリティ
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

        %% 継承関係
        INameElement <|.. BaseElement : implements
        BaseElement <|-- TextElement
        BaseElement <|-- PositionElement
        BaseElement <|-- BaseCounter
        ICounter <|.. BaseCounter : implements
        BaseCounter <|-- NumericCounter
        BaseCounter <|-- BlenderCounter
        BaseCounter <|-- AlphabeticCounter
        IRenameTarget <|.. BaseRenameTarget
        BaseRenameTarget <|-- ObjectRenameTarget
        BaseRenameTarget <|-- PoseBoneRenameTarget
        BaseRenameTarget <|-- MaterialRenameTarget
        INamespace <|.. Namespace

        %% 依存関係と関連
        ElementRegistry --> INameElement : creates >
        ElementRegistry --> ElementConfig : uses >
        NamingPattern --> INameElement : contains 1..*
        NamingPattern --> ElementConfig : configures >
        PatternRegistry --> NamingPattern : manages *
        PatternConfigManager --> PatternRegistry : uses 1
        PatternConfigManager --> ElementRegistry : uses 1
        PatternConfigManager --> ElementConfig : creates >
        
        NamespaceCache --> INamespace : manages *
        NamespaceCache --> IRenameTarget : uses create_namespace
        TargetCollection o-- IRenameTarget : contains
        
        ConflictResolver --> NamespaceCache : uses 1
        ConflictResolver --> IRenameTarget : resolves for * 
        ConflictResolver --> NamingPattern : uses for conflict resolution
        
        RenameResult --> IRenameTarget : references 1
        RenameContext --> IRenameTarget : contains *
        RenameContext --> RenameResult : produces *
        RenameContext --> NamingPattern : uses 1
        
        RenameService --> PatternRegistry : uses 1
        RenameService --> ConflictResolver : uses 1
        RenameService --> TargetCollection : uses 1
        RenameService --> RenameContext : creates >
        RenameService --> RenameResult : creates *
        
        RENAME_PT_main_panel --> RenameProperties : uses 1
        RENAME_OT_execute --> RenameService : uses 1
        RENAME_UL_patterns --> PatternRegistry : displays 1

        %% コンポジション関係
        NamingPattern "1" o-- "*" INameElement : contains
        PatternRegistry "1" o-- "*" NamingPattern : registers
        NamespaceCache "1" o-- "*" INamespace : caches
        TargetCollection "1" o-- "*" IRenameTarget : contains
        
        %% 依存関係（詳細）
        RenameService "1" --> "1" PatternRegistry : depends on
        RenameService "1" --> "1" ConflictResolver : depends on
        RenameService "1" --> "1" TargetCollection : depends on
