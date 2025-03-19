# 略式コード

# ConflictResolverはIRenameTargetをNamespaceMngに渡す→NSMはTrgに紐づくNSを初期化、既に初期化されていれば継続して利用する。→ NSMがCRに結果を返す。→CRは重複があればNamingPatternにカウンターのインクリメントを指示する。→再度NSMへ照会し、重複が解消されるまで、繰り返す。→重複が解消されたら、NSMにNSの更新を依頼し、FinalNameを呼び出し元に返す。

class RenameService:
    def execute_batch(self, targets: List[IRenameTarget], pattern: NamingPattern, strategy: str) -> List[RenameResult]:
        """
        一括リネームを実行する
        """
        results = []
        
        # 1. 各ターゲットについて名前を解決
        for target in targets:
            # 1.1 パターンから提案名を生成
            proposed_name = pattern.render_name()
            
            # 1.2 競合を解決（名前空間の更新も内部で行われる）
            final_name = self.conflict_resolver.resolve_name_conflict(
                target, pattern, proposed_name, strategy
            )
            
            # 1.3 結果を記録
            results.append(RenameResult(
                target=target,
                original_name=target.get_name(),
                proposed_name=proposed_name,
                final_name=final_name,
                success=True
            ))
        
        # 2. 解決済みの名前を実際のBlenderオブジェクトに適用
        for result in results:
            result.target.set_name(result.final_name)
        
        return results


# 使用例
service = RenameService()

# 1. ターゲットの収集
targets = service.target_collector.collect("object", context)

# 2. パターンの取得
pattern = service.pattern_registry.get_pattern("my_pattern")

# 3. 一括リネームの実行
results = service.execute_batch(
    targets=targets,
    pattern=pattern,
    strategy=ConflictResolver.STRATEGY_COUNTER
)

# 4. 結果の確認
for result in results:
    print(f"{result.original_name} -> {result.final_name}")

















class ConflictResolver:
    def resolve_name_conflict(
        self,
        target: IRenameTarget,
        pattern: NamingPattern,
        proposed_name: str,
        strategy: str,
    ) -> str:
        """
        ターゲットの名前競合を解決する
        """
        if not proposed_name:
            return ""

        # 1. IRenameTargetをNamespaceManagerに渡して名前空間を取得
        namespace = self._get_namespace(target)
        if not namespace:
            return proposed_name

        # 2. 名前空間で重複チェック
        if not self._is_name_in_conflict(proposed_name, namespace, target):
            return proposed_name

        # 3. 重複ありの場合、戦略に応じて解決
        if strategy == self.STRATEGY_COUNTER:
            return self._resolve_with_counter(pattern, proposed_name, namespace)
        elif strategy == self.STRATEGY_FORCE:
            return self._resolve_with_force(proposed_name)

        return proposed_name

    def _resolve_with_counter(
        self, pattern: NamingPattern, name: str, namespace: INamespace
    ) -> str:
        """
        カウンター要素を使用して名前競合を解決する
        """
        # カウンター要素を探す
        counter_elements = [e for e in pattern.elements if hasattr(e, "increment")]

        if not counter_elements:
            # カウンター要素がない場合は単純にサフィックスを追加
            suffix = 1
            new_name = f"{name}.{suffix:03d}"

            while namespace.is_name_in_conflict(new_name):
                suffix += 1
                new_name = f"{name}.{suffix:03d}"
                if suffix > 999:
                    break

            return new_name

        # カウンター要素を使用
        counter = counter_elements[-1]

        # 競合が解消されるまでカウンターを増分
        iterations = 0
        max_iterations = 1000

        while iterations < max_iterations:
            counter.increment()
            new_name = pattern.render_name()

            if not namespace.is_name_in_conflict(new_name):
                return new_name

            iterations += 1

        return f"{name}_unsolved_conflict"

class NamespaceManager:
    def get_namespace(self, target: IRenameTarget) -> INamespace:
        """
        ターゲットに紐づく名前空間を取得（なければ初期化）
        """
        key = target.get_namespace_key()
        
        # 既存の名前空間があれば返す
        if key in self.namespaces:
            return self.namespaces[key]
            
        # 新しい名前空間を初期化
        namespace = self._create_namespace(target)
        self.namespaces[key] = namespace
        return namespace

    def _create_namespace(self, target: IRenameTarget) -> INamespace:
        """
        ターゲットの種類に応じた名前空間を作成
        """
        factory = self._namespace_factories.get(target.target_type)
        if not factory:
            raise ValueError(f"Unknown target type: {target.target_type}")
        return factory(target)

"""
# 混乱の原因分析と改善案レポート

## 混乱の原因

1. **Namespaceの役割の誤解**:
   - 私はNamespaceが「実際のBlenderオブジェクトの状態」と「シミュレーション状態」を区別して管理する必要があると誤解していました。
   - 実際には、Namespace自体がすでにシミュレーション空間であり、実オブジェクトの更新はIRenameTargetのset_nameで行われる点を理解していませんでした。

2. **コードの一貫性の欠如**:
   - 「シミュレーション関連メソッド削除」の指示を受けて修正しましたが、RenameServiceの対応するメソッドまで追跡・修正できておらず、不整合が発生しました。
   - ConflictResolverからシミュレーション関連メソッドを削除しても、それらを呼び出すRenameServiceのコードを同時に修正しなかったため問題が残りました。

3. **既存コードの役割理解不足**:
   - RenameServiceの`_process_target`と`_apply_results`メソッドの関係性を正確に把握していませんでした。
   - これらは「名前解決」と「実際の適用」の2段階プロセスを実現していることを認識せず、不適切な変更を提案しました。

4. **修正の不完全さ**:
   - 一部のファイルは修正したものの、他の関連ファイルは変更せず、全体として一貫性のない状態になりました。
   - 特にRenameServiceの修正が行われず、削除したメソッドを呼び出す箇所が残りました。

## 改善案

1. **総合的なコード分析の徹底**:
   - 修正する前に、すべての関連ファイル（RenameService、ConflictResolver、Namespace）の依存関係を完全に把握する。
   - 一部のコンポーネントだけでなく、システム全体としての挙動を理解する。

2. **ConflictResolverとRenameServiceの適切な修正**:
   - ConflictResolverから不要なシミュレーションメソッドを削除。
   - RenameServiceの`_process_target`と`_apply_results`メソッドを修正して、削除したメソッドを使わないようにする。
   - 名前空間の更新は直接INamespaceのメソッドを使用するように変更。

3. **具体的なコード修正例**:

RenameServiceの_process_targetメソッド内で:
```python
# 変更前
self.conflict_resolver.simulate_namespace_update(target, original_name, final_name)

# 変更後
namespace = self.conflict_resolver._get_namespace(target)
if namespace:
    namespace.update(original_name, final_name)
```

RenameServiceの_apply_resultsメソッド内で:
```python
# 変更前
self.conflict_resolver.apply_namespace_update(result.target, old_name, result.final_name)

# 変更後
# Blenderオブジェクトのみ更新（名前空間は処理済み）
# 何もしない、またはエラーハンドリングのみ
```

4. **シーケンス図の更新**:
   - 更新したシーケンス図では、ConflictResolverとNamespaceManagerの正確な関係を反映させる。
   - 「名前解決」と「実際の適用」の2段階プロセスを明確に示す。

5. **設計原則の再確認**:
   - Namespaceの役割: シミュレーション空間としての名前管理
   - ConflictResolver: 名前競合の検出と解決
   - RenameService: 一括リネームプロセスの管理と実行

これらの改善を実施することで、コードの一貫性を確保し、設計意図に沿った実装を実現できます。
"""