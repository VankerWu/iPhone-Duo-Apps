# iPhone Duo App

独立的 iPhone Duo 应用适配信息目录，面向中文用户。帮助用户了解哪些应用出现在苹果公开介绍中、哪些经过社区实测、哪些尚待确认。

🌐 **网站：** https://vankerwu.github.io/iPhone-Duo-Apps/

> **非 Apple 官方项目。**「官方介绍」不等于本站已完成真机测试；未验证的应用会明确标注。

## 网站功能

- 应用搜索、分类和地区筛选、适配状态查看
- 自动同步 Apple App Store 官方图标、开发者、版本和商店详情页链接；未准确匹配则显示商店搜索入口
- 应用详情及原始证据链接
- GitHub Issues 社区反馈与纠错
- 深色 / 浅色主题，以及手机与桌面自适应
- 通过 GitHub Actions 补充公开 App Store 元数据；新增应用默认待验证
- 「赞赏作者」区域（二维码由站长自行提供，可选择性赞赏）

## 适配状态

- **苹果官方介绍**：公开资料中出现，但不自动等同于本站实测。
- **用户实测**：有经审查的设备、版本和画面证据。
- **待确认**：暂时没有充分适配证据。

## 支持作者

网站可免费访问，反馈和数据查询无须赞赏。若你愿意支持维护者，可访问网站底部「赞赏作者」区。赞赏完全自愿，不影响数据判断。

站长如果需要启用二维码，请把自己有权公开的图片按如下文件名放进 `docs/assets/`：

- `wechat-pay.png` — 微信赞赏码
- `alipay-pay.png` — 支付宝收款码

图片正确加载后自动隐藏“尚未添加”的占位提示；图片加载失败时只显示占位提示。二维码被限制为最大 184×184 像素（窄屏 158×158）。建议上传**仅包含可扫描二维码、保留白边**的正方形图片，不要上传带昵称、导航栏、额外页面文字的整张收款界面截图。请使用你自己的收款码，不要上传他人的账号或敏感信息。

## 运行与部署

这是独立编写的静态网站，无需安装前端依赖。网站入口是 `docs/index.html`，可在本地浏览器预览。GitHub Pages 使用 **main /docs** 发布。

源码位于 `docs/`，应用数据位于 `docs/data/apps.json`，前端逻辑为 `docs/assets/app.js`，样式位于 `docs/assets/styles.css`。

仓库地址：https://github.com/VankerWu/iPhone-Duo-Apps

## 数据与版权

App 名称、品牌和图标属于各自权利人；目录整理以可核查证据为原则，禁止无证据宣称已适配。详情参考 [DATA_POLICY.md](DATA_POLICY.md)。

该项目与 Apple 及被收录应用开发者无官方关联。仓库原创代码依仓库内 LICENSE 授权；第三方内容不因此获得授权。

欢迎通过 [Issues](https://github.com/VankerWu/iPhone-Duo-Apps/issues) 提交适配反馈。


## 自动获取 App Store 图标与官方链接

站点已配置 Apple 公开 iTunes Search/Lookup API 与苹果热门榜单 RSS 的自动同步程序：`scripts/refresh_metadata.py`。
同步成功后在 `docs/data/apps.json` 中填充 `artwork`（苹果 CDN 图标）、`appStoreUrl`（具体条目官方链接）、版本、开发者。**它绝不会把“出现在榜单”自动改成“已适配 Duo”。**

**首次使用：** GitHub 仓库进入 `Actions → Refresh public App Store data → Run workflow`。
第一次可稍后在提交历史中看到 `chore: refresh public App Store metadata`，网站 Pages 会读取新数据自动刷新。此 workflow 也有计划任务；如果提示没有写权限，需在 GitHub 仓库 `Settings → Actions → General → Workflow permissions` 允许读写权限，并确认没有禁用 Actions。

匹配以精确应用名称或已核对的苹果 App ID 为准。**匹配失败**的卡片显示“商店搜索”，打开苹果的官方搜索页，用户需确认开发者；不会用名称近似的 App 冒充确切结果。
部分 App 可能因地区商店、名称变动或接口限制而缺少图标；使用第三方图标和营销内容应遵守 Apple Search API 的使用条款，并将图标用于推广对应 App Store 条目。
