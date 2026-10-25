# Duo Atlas — iPhone Duo 适配观察站

> 一个独立、中文优先、开源的 iPhone Duo App 适配信息目录。**收录并不代表适配；没有证据，不给绿色勾。**

![DuoAtlas 网站桌面预览](screenshots/desktop.png)

这是一个可直接部署到 GitHub Pages 的纯静态网站，使用自己编写的 HTML、CSS、JavaScript 和 Python，不依赖第三方商业模板、其他同类网站的源码或数据库。

## 目前已经实现

- [x] 原创响应式网页（手机/桌面）、浅色/深色主题切换
- [x] 应用名称/开发者/功能搜索，地区/类别/状态筛选与排序
- [x] 应用详情、公开证据、App Store 链接（同步到元数据后）
- [x] 数据状态清楚分成「苹果官方介绍」「用户实测」「待验证」
- [x] 第一批 **45 款应用**：33 款来自 Apple 2026 年 10 月 22 日官方介绍，12 款作为待确认的热门观察对象
- [x] GitHub Issues 实测提交、纠错入口
- [x] GitHub Actions 自动补充国区、美区 App Store 热门榜单，并获取公开元数据（默认每天两次）
- [x] 不自动把“有更新”判断为“已适配”

> 注意：首批 33 款的准确标签是「苹果官方介绍」，**不是本站已完成 33 次真实设备测试**。用户实测栏目初始为零，是刻意如实展示。排行榜新加入的 App 一律是「待确认」。

## 🚀 第一次上传到 GitHub（最简单方法）

建议新建 **DuoAtlas** 独立仓库，**不要把网站和 DuoCinema 视频播放器混成一个仓库**。

1. 解压这个 ZIP 到电脑，例如 `Downloads/DuoAtlas_website`。
2. 打开 GitHub Desktop，选择 **File → Add Local Repository**，选择解压的整个文件夹。
3. 如果提示目录不是 Git 仓库，点击 **create a repository**，名称最好保持当前文件夹名以免另建空文件夹；不要勾选自动创建 README，因为文件夹里已有 README。
4. 创建成功后，点击 **Commit to main**；然后点击 **Publish repository**，名称可以改成 `DuoAtlas`，取消 `Keep this code private` 以公开。
5. 用网页进入 GitHub 的 `DuoAtlas` 仓库，点击 **Settings → Pages**，在 **Build and deployment** 里选择 **Deploy from a branch**；Branch 选 **main**，目录选 **/docs**，点击 **Save**。
6. 等 GitHub Pages 部署显示成功，再访问（仓库名确为 `DuoAtlas` 时）：

   **`https://VankerWu.github.io/DuoAtlas/`**

   这是按标准规则推导的预期地址，**不是已经上线的网站**。实际地址以 GitHub Pages 设置页显示为准。

7. 网页的「提交报告」按钮使用 `VankerWu/DuoAtlas` 作为仓库地址。如果你的新仓库名字不同，修改 `docs/assets/app.js` 第一段的 `REPOSITORY` 常量。
8. 若 GitHub Issues 未启用，进入 **Settings → General → Features → Issues** 打开。这样粉丝可以提交反馈。

### 自动更新怎么开启

仓库打开 **Actions** 页，允许工作流运行。此项目提供 `.github/workflows/refresh-metadata.yml`：

- 可在 Actions → **Refresh public App Store data** → **Run workflow** 手动触发第一次自动收录。
- 以后每天 **03:27 UTC / 15:27 UTC** 自动查询（GitHub 不保证精确到分运行）。
- 自动增加国区、美区 Top Free 榜单上的应用，**统一标记为待验证**；同时尽量同步 App Store 上公开的版本/图标/链接等资料。
- 若提交失败，检查仓库 **Settings → Actions → General → Workflow permissions** 是否允许该工作流写入仓库内容；若仓库启用了 main 分支保护规则，可能需要改为 Pull Request 流程。
- iTunes 搜索/查找有网络限制与速率限制；某些 App 可能无法匹配，系统会保留原有数据，**不会强行套用相似名称**。

## 🗂 文件结构

```text
DuoAtlas_website/
├── docs/                  # 网站文件，GitHub Pages 从这里部署
│   ├── index.html
│   ├── assets/
│   │   ├── app.js
│   │   ├── styles.css
│   │   └── favicon.svg    # 本项目独立原创的图标
│   └── data/apps.json      # 内容数据库，可手工编辑
├── scripts/
│   └── refresh_metadata.py
├── .github/
│   ├── workflows/refresh-metadata.yml
│   └── ISSUE_TEMPLATE/
├── README.md
├── DATA_POLICY.md
├── CONTRIBUTING.md
└── LICENSE
```

## 在 Mac 本地预览

**可以直接双击 `docs/index.html` 预览首批 45 款数据**（页面内置离线示例副本）。如果你希望预览编辑后 `data/apps.json` 的最新内容，推荐：

```sh
cd DuoAtlas_website
python3 -m http.server 8080 --directory docs
```

浏览器访问 `http://localhost:8080`。如果你不想碰终端，按前面的步骤上传 GitHub 后直接访问 Pages 地址。

## 添加或修正一款 App

编辑 `docs/data/apps.json`：

- `id` 唯一；`name` 显示名称；`category` 类别；`region` 为中国大陆/全球/美国/韩国等。
- `status` 只能填写：`apple_featured`、`community_verified` 或 `unverified`。
- `sourceUrl` 填公开、可核查的**原始证据**，没有证据就留空。
- **永远不要根据更新日期或“采用较新 SDK 的猜测”把状态自动升为已适配**。
- 要把 App 改成 `community_verified`，必须经过人工审查，核对 app 版本、Duo 姿态、画面与截图。
- 不发布私密照片、账号资料、盗版影视素材或未经授权的截图。

## 原创性与版权

- 代码、布局、SVG 标识为此独立项目重新编写；没有复制类似查询站的前端源码、设计模板或数据库。
- 应用名称、事实、公开更新日期不等于可独占的创意作品。每条内容尽量留来源链接。
- 任何 App Store 图标由对应开发者拥有权利；元数据更新引用 Apple 公开 API 的图标 URL，使用时必须遵循 Apple 的 [Search API 使用条款](https://performance-partners.apple.com/search-api)。站点链接到对应的 App Store 产品页。不需要图标时，可以只使用本站原创的渐变首字母占位图。
- Apple、iPhone、App Store 是其各自权利人商标。本项目与 Apple 无关联。
- MIT 许可证仅适用于仓库中作者原创的代码和原创视觉素材，不向你授予第三方应用名称、图标、截图或商标的权利。

## 参考证据

- Apple Newsroom（2026-10-22）：https://www.apple.com/newsroom/2026/10/developers-bring-incredible-new-app-experiences-to-iphone-duo/
- Apple 官方开发指南：https://developer.apple.com/iphone-duo/prepare/
- Apple iTunes Search API：https://performance-partners.apple.com/search-api

## 发布前检查

- [ ] GitHub 仓库为 **Public**。
- [ ] Pages 选择 **main /docs**。
- [ ] 打开 Pages 实际地址，试搜索、筛选、点击 App 详情。
- [ ] 点击「提交你的发现」能打开**新网站仓库**的 GitHub Issues，而不是旧的 DuoCinema 仓库。
- [ ] 检查全部标为「苹果官方介绍」的条目确实有可核查的来源。
- [ ] 确认未上传密码、令牌或个人信息。
- [ ] 自动刷新工作流首次运行无错误。
