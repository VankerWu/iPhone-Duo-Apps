# V13：增加美区 App Store 检测

基于线上仓库 f83115e，保留 V12 的简洁页面、软件/游戏分类、人工提交入口与历史更新记录。README、CSS、赞赏区域、已收录数据和审核结果未改动。

## 如何升级

完整 ZIP 内有两个文件夹：

- `UPGRADE_ONLY`：仅包含本次需要上传/替换的文件。
- `iPhone-Duo-Apps`：完整源码及制作时的数据快照。

**给现有仓库升级，请只把 UPGRADE_ONLY 内的文件按原路径上传到仓库根目录。不要把 UPGRADE_ONLY 文件夹本身传上去。**

不要覆盖 `docs/data`、`docs/updates` 或 README。若你在制作本包后又修改了相同程序文件，应先合并差异；包内快照不能覆盖更新的线上数据。Mac 使用 Command+Shift+. 显示隐藏的 `.github` 目录。

本次程序文件：

1. `.github/workflows/discover-duo-apps.yml`
2. `scripts/discover_duo_apps.py`
3. `scripts/discover_us_apps.py`（新增）
4. `scripts/storefront_data.py`（新增）
5. `scripts/refresh_metadata.py`
6. `scripts/store_categories.py`
7. `scripts/report_sync.py`
8. `docs/assets/app.js`
9. `docs/assets/catalog.js`
10. `docs/assets/updates.js`
11. `docs/index.html`
12. `tests/test_catalog.cjs`
13. `tests/test_v11_categories.py`
14. `tests/test_v13_storefronts.py`（新增）

`V13_UPGRADE.md` 和 `V13_FILES.json` 为安装说明和文件校验清单，可一并上传。

## 生效与查看

安装后在 Actions 手动运行 `Discover Duo app leads and refresh metadata` 一次。计划保持每小时第23分钟运行。GitHub 定时任务可能延迟或漏触发；需要真实 event=schedule 记录确认，配置存在不代表调度已验证。

工作流在原命令后启用 `--storefronts cn us`。直接运行脚本时默认仍为 `cn`，兼容旧调用。可用 `--storefronts us` 仅运行美区。

网站地区筛选选“美国”可看到美区条目，以及已获取美区资料的跨区条目。详情页按地区显示商店链接、版本和开发者声明。旧“主要地区”字段保留，表示原收录地区，不等于所有可用地区。

更新记录仍列出新增软件/游戏、已有App版本变化、适配线索。新增记录附国区/美区标识；“地区商店资料变化”单独放在其他更新中。已收录App首次获取美区资料不会重复算新增。历史报告无需迁移。

## 扫描范围和频率

国区原有总榜、分类、游戏、优先关注、候选池和网页补查继续运行。

美区新增：

- 免费、付费总榜前100；英语关键词搜索。
- 每轮轮询8个主分类、6个游戏子分类的免费/付费榜。
- 独立持久候选池 `discoveryPoolUS` 和各类 US 游标，不移动国区游标或用美区池替换国区池。
- 每轮最多600个候选ID批量查询；轮询最多30个美区网页的可见版本历史。
- 美区阶段默认12分钟软预算，达到预算后在请求边界停止，其余候选下轮继续。单个在途请求及重试可能略超出预算；整个工作流仍有45分钟上限。

只有明确写出 iPhone Duo 并含支持、适配、布局等表述且未命中已识别的否定/计划用语，才进入待确认。普通更新、名称相似、分类或榜单排名不能独立触发收录。当前仍是启发式文字筛选，不能保证无误检或无漏检，也不代替真机验证。

## 数据与审核保护

- 按 App Store 数字ID去重；同名不同ID不自动合并。
- 同ID的国区、美区商店资料分别放在 `storeListings`，声明分别放在 `storeDiscoveries`，分类分别放在 `storeCategories`。
- 旧字段继续保留；另一地区的资料不覆盖原条目的主版本、主链接和人工名称。
- 审核队列保留原 `firstSeen`、`reviewStatus`、人工批注及额外字段；分区证据追加在 `storeEvidence`。原人工拒绝条目不会换个地区重新自动发布。
- 不改变 `status`、`note`、`sourceLabel`、`sourceUrl`、`sourceDate`、`verifiedDate`，不把开发者声明升级为“苹果官方介绍”或“用户实测”。
- 美区声明仅表示对应地区和证据版本；不能推出国区版已适配。历史版本声明也不证明之后每个版本都适配。
- Lookup未返回某个ID不代表下架；已观测到的商店资料只是观测记录，不保证永久可用。
- 任一地区扫描异常时回退其未完成修改，保留另一地区成功结果；报告说明 failed/partial。全部地区失败时不写入本轮目录和队列。

## 验证及当前限制

- 51项Python测试通过，覆盖跨区去重、人工审核字段、地区独立证据、分类、版本不降级、部分失败、时间预算、报告不重复计数。
- 前端筛选规则测试和脚本语法检查通过；桌面及手机端的浏览器显示效果仍需验证。
- 真实美区分类接口解析99个ID，Fantastical的美区Lookup读取到明确声明，网页解析25条版本记录；使用真实响应回放验证美区收录和报告。
- 美区总榜接口抽查两次超时，因此未宣称所有来源均可访问；代码对来源失败保留统计并继续其他来源。
- 安装后请运行完整双区流程，并查看 Actions 报告中的两个地区结果。
- 不能穷举全App Store。榜外、搜索未返回、未声明、来源延迟或页面结构变化的应用仍可能漏掉；候选池越大，完整轮询越久。
