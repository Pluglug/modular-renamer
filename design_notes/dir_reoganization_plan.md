-- core
  -- base
    -- base_element.py  # INameElement, BaseElement
    -- base_counter.py  # ICounter, BaseCounter
    -- base_target.py   # IRenameTarget, BaseRenameTarget 
    -- base_namespace.py  # INamespace, Namespace
  
  -- blender
    -- outliner.py      # outliner関連機能を統合
    -- pointer_cache.py # PointerCache
    -- constants.py     # Blender固有の定数
  
  -- elements
    -- registry.py      # ElementRegistry
    -- factory.py       # エレメント作成関連
  
  -- pattern
    -- model.py         # NamingPattern
    -- cache.py         # PatternCache
    -- factory.py       # PatternFactory
    -- facade.py        # PatternFacade
  
  -- target
    -- registry.py      # RenameTargetRegistry
    -- collector.py     # TargetCollector
    -- scope.py         # OperationScope, CollectionSource
  
  -- namespace
    -- manager.py       # NamespaceCache
    -- conflict.py      # ConflictResolver
  
  -- service
    -- rename_service.py  # RenameService
    -- rename_context.py  # RenameContext, RenameResult
  
  -- config.py          # システム全体の設定
  -- constants.py       # 一般的な定数
  -- __init__.py        # 公開API

注:
property_gはui層へ