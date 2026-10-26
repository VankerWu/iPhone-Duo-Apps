# iPhone Duo App：以后不再手动更新文件

这一套功能只需要往 GitHub 仓库上传一次。之后可以直接在手机浏览器使用 GitHub Issues 管理新应用，不需要 GitHub Desktop，也不用修改 README、HTML 或 JSON。

## 你自己添加

打开：https://github.com/VankerWu/iPhone-Duo-Apps/issues/new?template=new-app.yml

填写 App 名称、App Store 链接（建议必填）、分类、地区、线索，提交 Issue。
只要使用仓库拥有者 VankerWu 账号，标题以 `[收录]` 开头，GitHub Actions 自动写入 docs/data/apps.json，标注「待确认」。

## 粉丝提交

粉丝也用同一页面提交。为了防止恶意或不实信息，粉丝的 Issue 不会直接修改网站。
你看完 Issue 后，自己在该 Issue 下评论**只有**：`/收录`
GitHub Actions 才会将该 App 添加到网站的「待确认」名单。需有更多截图和版本证据，才能在未来人工改为「用户实测」。

## 更新的过程

GitHub Actions 会读取 App Store 商品 ID，检查官方元数据，在网站数据中添加条目。随后自动提交代码，GitHub Pages 自动部署。
如果该 App 已存在，只追加反馈来源记录，不会重置原有的官方/实测结论。

如果 Apple API 暂时不可用：填写了准确商品链接的条目仍可先添加，网站会尝试加载官方图标。没填官方链接、又无法唯一匹配时，自动任务会评论提醒补充链接。修改 Issue 内容后，回复 `/收录` 重新尝试。

## 一次性安装

把本压缩包中的 `.github/`、`scripts/` 和 `docs/以后这样添加App.md` 合并到现有 `iPhone-Duo-Apps` 仓库根目录。
**不要**覆盖 `docs/data/apps.json`、网站的 README、赞赏码及前端页面。
GitHub Desktop 先 Pull → 拷贝合并 → Commit → Push。
如果遇到远程版本更新冲突，先 Pull，解决冲突后再 Push，**不要强制推送**。

需要在 GitHub 仓库 Settings → Actions → General 中确认 Workflow permissions 允许 Read and write permissions；也可直接检查此工作流能否成功写入文件。若 main 有分支保护，需对 bot 开通写入或改用 PR 工作流。

首次安装后，使用自己的账号提交一条新 App 测试，观察 Actions → Add approved App reports to site 是否为绿色，随后检查网站。网站图标可稍后由 Apple Lookup 补齐。

## 安全与局限

仅仓库所有者本人创建的收录 Issue 自动进入网站，其他用户必须由所有者评论 `/收录` 才会进入。
入库仅为「待确认」；不把单条微博反馈、App Store 版本更新当作适配实测结论。
这个功能不会自动抓取微博评论；微博评论仍需要你把 App 名称提交成一条 Issue。
