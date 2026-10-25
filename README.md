# iPhone Duo App — 折叠屏应用适配目录

查询 iPhone Duo 应用适配资料，区分苹果官方介绍、用户实测和待确认状态。
网站地址：https://vankerwu.github.io/iPhone-Duo-Apps/

## App Store 官方图标与直达链接（V4）

- 45 款首批应用已根据 **Apple 官方 App Store 商品页**预置准确的 **App ID**，页面内每个 App 都有直达详情页的链接（不是搜索页）。
- 图标并非手绘、抓取其他网站或以文字充当官方图标。官方图标由 Apple iTunes Lookup API 提供。页面打开后会尝试按 ID 实时载入；GitHub Actions 也会定期把 URL/版本/图标地址写入 `docs/data/apps.json`。
- 苹果暂时未返回图片或访客网络无法访问时，显示中性占位图；**不会把假图标说成 App Store 图标**。
- `App Store` 链接是官方应用页面，**不代表该 App 已经得到 Duo 适配实测确认**。访问者所在地区可能需要切换 App Store 区域。

### 使图标长期稳定显示（必做一次）

1. 在 GitHub 上传/覆盖这个版本的文件并 Push。
2. 打开仓库 **Actions → Refresh public App Store data → Run workflow**，选 `main` 分支运行。
3. 检查运行日志，观察 `official artwork: N/45`。成功后工作流会将元数据更新提交回 `main`，Pages 自动部署。
4. 以后每 12 小时自动更新。不强制把名称相似的 App 匹配在一起。

如果 Actions 无权限写回仓库：**Settings → Actions → General → Workflow permissions → Read and write permissions**。修改仓库设置之前应确认自己了解相应权限。

### 直接本地运行同步脚本（可选）

```bash
python3 scripts/refresh_metadata.py --no-charts
```

这个脚本需要电脑联网。它仅获取公开 App Store 资料，不抓取账号、下载 IPA 或修改任何适配判定。

## 网站源码

- `docs/index.html` — GitHub Pages 入口
- `docs/assets/app.js` / `styles.css` — 交互和样式
- `docs/data/apps.json` — 目录及商店 ID
- `.github/workflows/refresh-metadata.yml` — 定时图标/版本同步
- `scripts/refresh_metadata.py` — 苹果 API 数据同步代码

## 关于站点

这是第三方独立项目，与 Apple 及各应用开发者无官方隶属关系。App 图标、名称与商标归各自权利人所有。使用 Apple 官方 API 中的宣传素材时，请遵守 Apple 相关条款，并将图标与商店入口一起展示。
