# V11 最终版升级说明

本版完成「软件 / 游戏、官方用途分类、游戏子分类检索、分组更新报告」升级，取代此前不完整的 V10 包。基于公开仓库 main 的 7bdaa3f 制作。

## 实际功能

- 目录新增全部 / 软件 / 游戏筛选，可与关键词、地区、用途分类和适配状态组合使用。
- 按国区 Apple Lookup 返回的 primaryGenreId、genreIds 归类；主要分类用于展示，接口返回的其他分类也可用于筛选。游戏展示动作、策略、角色扮演等子分类。
- 「新适配线索」改为独立标签和可选过滤条件，不再占用分类下拉菜单。
- 原有苹果官方介绍、用户实测、待确认保持独立；新自动线索始终待确认。普通版本更新不会据此判为适配。
- 增加18个游戏子分类榜单的轮询配置，每轮6个子分类，各取免费/付费榜前100；在原分类轮询之外增补，继续检查版本说明。仅国区，沿用两小时一次。
- 报告分别列出新增软件、游戏、类型待同步条目；保留版本更新与适配线索变化的独立名单，并提供微博文案复制、历史批次和最近收录排序。
- 保留人工提交入口、审核流程、捐赠区域及现有视觉样式。

## 两个 ZIP 怎么使用

**iPhone-Duo-Apps-V11-update-only.zip：用于升级你正在运行的仓库。**
解压后按原有路径上传其中的 docs、scripts、tests 文件夹，以及说明文件。它没有 apps.json、审核队列、旧更新报告和 README，所以不会用旧快照覆盖这些内容。文件夹应与仓库根目录的 docs、scripts、tests 对齐，不要多套一层目录。需要一次提交包含所有新脚本与分类 JSON，避免只上传网页。

**iPhone-Duo-Apps-V11-full-source.zip：完整源码备份或从零部署使用。**
内含 iPhone-Duo-Apps 外层目录。不要将该目录作为嵌套文件夹上传到现有仓库；升级现有仓库优先使用上面的升级包。

上传后检查 Pages 部署完成，再手动运行一次 Actions → Discover Duo app leads and refresh metadata → Run workflow。后续保持两小时一次的现有设置。报告选择器从升级后逐轮积累，保留最近100轮；旧 Markdown 报告仍能从“全部历史报告”访问。

## 替换文件（7个业务文件 + 4个原有测试文件）

- docs/index.html
- docs/assets/app.js
- docs/assets/styles.css
- scripts/discover_duo_apps.py
- scripts/refresh_metadata.py
- scripts/ingest_issue.py
- scripts/report_sync.py
- tests/test_discover_duo_apps.py
- tests/test_ingest_issue.py
- tests/test_v8_reports.py
- tests/test_v9_cn.py

## 新增文件

- docs/assets/catalog.js：组合筛选规则。
- docs/assets/updates.js：分组更新清单、历史批次和复制微博文案。
- docs/data/app-store-genres.json：Apple 官方国区分类 ID 与中文名称。
- docs/data/app-categories-cn.json：本次获取的已有应用分类缓存，不包含适配判定。
- scripts/store_categories.py：统一分类同步规则。
- scripts/sync_categories.py：可选的分类缓存刷新，仅写分类缓存，不改应用目录和审核队列；日常工作流通过原有刷新步骤自动同步分类，无需额外运行它。
- scripts/priority_apps_cn.json：每轮优先检查的应用 ID；不是适配证据。
- tests/test_v10_upgrade.py
- tests/test_v11_categories.py
- tests/test_catalog.cjs
- V11_UPGRADE.md、V11_FILES.json：说明和校验清单。

无需替换 README.md、.github/、docs/data/apps.json、docs/data/duo-review-queue.json、docs/updates/、赞赏二维码。

## 数据与分类

原有286个条目、人工分类字段、备注、引用来源、审核决定全部保留。什么值得买、酷安本来已经收录，本次不会重复添加。

本次只读取国区接口，为267个现有条目取得官方分类，其中265个软件、2个游戏。另19个未返回国区分类的条目继续保留在“全部”，显示分类待同步，不按名称猜测游戏或软件。它们可能不在国区提供，仍保留原有链接和结论。

分类写入独立的 storeCategory 元数据；旧人工 category 字段保留。网页优先读应用中的新分类，缺少时使用独立分类缓存。自动发现的新条目同时附官方分类；分类信息缺失不会删除条目或改变审核状态。

候选池与榜单并不能代表全部国区应用。游戏子分类是分轮次尝试抓取，并非每两小时全量扫描；接口失败、页面结构改变或未公开版本说明仍可能漏检。

## 验证

- 36项 Python 测试通过，覆盖保留人工字段、未返回分类、游戏证据门槛、轮询、重复收录、报告分组和历史记录。
- Node 分类行为测试通过，JavaScript 语法检查通过。
- 真实 Chromium 验证了286条目录、软件/游戏切换、动作子分类、购物、分类待同步、搜索与状态组合、历史切换、文案复制与失败回退，以及桌面、390px和320px布局。
- 实际请求国区动作免费榜，返回100条榜单记录；未在本环境运行完整发现流程，也未将代码推送或部署到你的 GitHub。
- README、应用目录、审核队列和工作流与基线逐字节一致。

## 官方资料

- https://developer.apple.com/app-store/categories/
- https://itunes.apple.com/WebObjects/MZStoreServices.woa/ws/genres?id=36&cc=cn
- https://performance-partners.apple.com/search-api
