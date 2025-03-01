# Modular-Renamer 開発計画

## パッケージ構造

```
modular_renamer/
├── __init__.py                    # Blenderアドオン登録、バージョン情報
├── core/                          # コア機能
│   ├── __init__.py
│   ├── elements.py                # 名前要素の定義
│   ├── element_registry.py        # 要素登録システム
│   ├── namespace.py               # 名前空間管理
│   ├── pattern.py                 # 命名パターン
│   ├── pattern_registry.py        # パターン登録・管理
│   ├── rename_target.py           # リネーム対象インターフェース
│   ├── target_collector.py        # リネーム対象収集
│   ├── conflict_resolver.py       # 名前衝突解決
│   └── rename_service.py          # リネーム処理統合サービス
│
├── ui/                            # ユーザーインターフェース
│   ├── __init__.py
│   ├── panels.py                  # UIパネル
│   ├── operators.py               # オペレーター
│   ├── list_templates.py          # リスト表示テンプレート
│   └── properties.py              # プロパティ定義
│
├── targets/                       # リネーム対象の具体的実装
│   ├── __init__.py
│   ├── object.py                  # 3Dオブジェクト
│   ├── bone.py                    # ボーン
│   ├── material.py                # マテリアル
│   ├── modifier.py                # モディファイヤ
│   └── node.py                    # ノード
│
├── elements/                      # 名前要素の具体的実装
│   ├── __init__.py
│   ├── text_element.py            # テキスト要素
│   ├── counter_element.py         # カウンター要素
│   ├── position_element.py        # 位置要素（L/R等）
│   └── blender_counter.py         # Blenderカウンター処理
│
├── utils/                         # ユーティリティ
│   ├── __init__.py
│   ├── logging.py                 # ログ機能
│   ├── config.py                  # 設定管理
│   └── validation.py              # 検証ユーティリティ
│
├── presets/                       # デフォルトプリセット
│   ├── __init__.py
│   ├── rigify_bones.json          # Rigifyボーン命名規則
│   ├── standard_objects.json      # 標準オブジェクト命名規則
│   └── materials.json             # マテリアル命名規則
│
├── tests/                         # テスト
│   ├── __init__.py
│   ├── setup.py                   # テスト環境セットアップ
│   ├── test_elements.py           # 要素テスト
│   ├── test_patterns.py           # パターンテスト
│   ├── test_namespace.py          # 名前空間テスト
│   ├── test_conflict.py           # 衝突解決テスト
│   ├── test_rename.py             # リネーム統合テスト
│   └── fixtures/                  # テストデータ
│       ├── test_armature.blend    # テスト用アーマチュア
│       └── test_scene.blend       # テスト用シーン
│
└── resources/                     # リソース格納先
    ├── user_presets/              # ユーザープリセット
    ├── user_patterns/             # ユーザーパターン
    └── export/                    # エクスポートした設定
```

## モジュールとクラスの役割

### core モジュール

#### elements.py
- `INameElement` (インターフェース): 名前要素の基本インターフェース
- `BaseElement` (抽象クラス): 名前要素の基本実装

#### element_registry.py
- `ElementRegistry`: 名前要素の登録・管理・生成

#### namespace.py
- `INamespace` (インターフェース): 名前空間インターフェース
- `NamespaceBase` (抽象クラス): 名前空間の基本実装
- `NamespaceManager`: 名前空間の管理

#### pattern.py
- `NamingPattern`: 命名パターン定義と名前構築処理

#### pattern_registry.py
- `PatternRegistry`: パターンの登録・検索・保存・読み込み

#### rename_target.py
- `IRenameTarget` (インターフェース): リネーム対象の統一インターフェース

#### target_collector.py
- `CollectionStrategy` (インターフェース): リネーム対象収集戦略
- `TargetCollector`: 収集戦略の統合と管理

#### conflict_resolver.py
- `ConflictResolver`: 名前衝突の検出と解決
- `ResolutionStrategy` (インターフェース): 衝突解決戦略のインターフェース

#### rename_service.py
- `RenameContext`: リネーム操作のコンテキスト情報
- `RenameService`: リネーム処理の中心的サービス

### ui モジュール

#### panels.py
- `RENAME_PT_main_panel`: メインリネームパネル
- `RENAME_PT_edit_panel`: パターン編集パネル
- `RENAME_PT_settings_panel`: 設定パネル

#### operators.py
- `RENAME_OT_execute`: リネーム実行
- `RENAME_OT_add_pattern`: パターン追加
- `RENAME_OT_add_element`: 要素追加
- その他操作オペレーター

#### list_templates.py
- `RENAME_UL_patterns`: パターンリスト表示
- `RENAME_UL_elements`: 要素リスト表示
- `RENAME_UL_element_items`: 要素アイテムリスト表示

#### properties.py
- `RenameSettings`: アドオン設定
- `RenameProperties`: シーンプロパティ

### targets モジュール

各ファイル（object.py, bone.py など）では、以下のクラスを定義:
- `XxxRenameTarget`: 特定タイプのリネーム対象実装
- `XxxNamespace`: タイプ固有の名前空間実装
- `XxxCollectionStrategy`: タイプ固有の収集戦略

### elements モジュール

各ファイルでは、それぞれの要素タイプの実装:
- `TextElement`: テキスト要素の実装
- `CounterElement`: カウンター要素の実装
- `PositionElement`: 位置指定要素の実装（L/R等）
- `BlenderCounterElement`: Blender自動カウンター処理

### utils モジュール

#### logging.py
- `ModularLogger`: ログ管理
- `DebugPanel`: デバッグ情報表示

#### config.py
- `ConfigManager`: 設定の保存と読み込み
- `UserPreferences`: ユーザー設定の管理

#### validation.py
- `PatternValidator`: パターンの検証
- `ElementValidator`: 要素設定の検証

## テスト計画

### テストモジュールの役割

#### setup.py
- `TestEnvironment`: Blenderバックグラウンドモード用テスト環境の構築
- `TestDataCreator`: テストデータの作成

#### test_elements.py
- 各要素タイプの単体テスト
- パターンマッチングと値抽出の検証
- 値設定と出力の検証

#### test_patterns.py
- パターン定義のテスト
- 名前構築ロジックのテスト
- パターン検証機能のテスト

#### test_namespace.py
- 名前空間管理のテスト
- 名前重複検出のテスト

#### test_conflict.py
- 名前衝突解決戦略のテスト
- カウンター増加と強制リネームのテスト

#### test_rename.py
- 完全な統合テスト
- 実際のBlenderオブジェクトを使用したリネームテスト

### テスト実行方法

1. バックグラウンドモード用のテストランナースクリプト:
```bash
blender --background --python tests/run_tests.py
```

2. 特定テストのみ実行:
```bash
blender --background --python tests/run_tests.py -- --test test_elements
```

3. テスト結果の出力先:
```
resources/test_results/
```

## リソース管理

### リソースの種類と保存先

1. **ユーザープリセット**:
   - 保存先: `resources/user_presets/`
   - 形式: JSON
   - 内容: ユーザー定義の命名規則プリセット

2. **ユーザーパターン**:
   - 保存先: `resources/user_patterns/`
   - 形式: JSON
   - 内容: ユーザー定義の命名パターン

3. **エクスポート設定**:
   - 保存先: `resources/export/`
   - 形式: JSON/YAML
   - 内容: プロジェクト間で共有するための設定

### リソース管理機能

1. **インポート/エクスポート**:
   - `ConfigManager.export_settings()`
   - `ConfigManager.import_settings()`

2. **プリセット適用**:
   - `PatternRegistry.apply_preset()`

3. **ユーザー設定保存**:
   - `UserPreferences.save()`
   - `UserPreferences.load()`

## 実装フェーズとマイルストーン

### フェーズ1: 基盤構築（2週間）
- コアインターフェースと基本クラスの実装
- テスト環境のセットアップ
- 最小限の機能テスト

### フェーズ2: 基本機能（2週間）
- オブジェクトとボーンのリネーム機能実装
- 基本的なUIパネル
- 簡易的なパターン管理

### フェーズ3: 拡張機能（2週間）
- 衝突解決戦略の実装
- 追加のリネーム対象サポート
- UI改善とフィードバック機能

### フェーズ4: 高度機能と最適化（2週間）
- プリセットシステム
- インポート/エクスポート機能
- パフォーマンス最適化

### フェーズ5: テストとドキュメント（2週間）
- 総合テスト
- ユーザードキュメント
- サンプルプリセット作成

## 結論

このModular-Renamerは、複雑なリネーム処理を整理された構造で提供するプロジェクトです。インターフェースベースの設計により、拡張性と保守性を確保し、将来的なリネーム対象や機能の追加を容易にします。また、テスト駆動開発を取り入れることで、複雑なリネームロジックの信頼性を担保します。

パッケージ構造は、責任ごとに明確に分割され、それぞれのコンポーネントが連携して動作します。特に名前空間管理と衝突解決の実装は、Blenderの自動リネームを超える柔軟性を提供し、大規模プロジェクトにおけるリネーム作業を効率化します。
