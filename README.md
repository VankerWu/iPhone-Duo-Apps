# iPhone Duo App

独立的 iPhone Duo 应用适配信息目录，面向中文用户。帮助用户了解哪些应用出现在苹果公开介绍中、哪些经过社区实测、哪些尚待确认。

🌐 **网站：** https://vankerwu.github.io/iPhone-Duo-Apps/

> **非 Apple 官方项目。**「官方介绍」不等于本站已完成真机测试；未验证的应用会明确标注。

## 网站功能

- 应用搜索、分类和地区筛选、适配状态查看
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

图片存在时网页会自动显示；未添加时仅显示“待添加”的提示。请使用你自己的收款码，不要上传他人的账号或敏感信息。

## 运行与部署

这是独立编写的静态网站，无需安装前端依赖。网站入口是 `docs/index.html`，可在本地浏览器预览。GitHub Pages 使用 **main /docs** 发布。

源码位于 `docs/`，应用数据位于 `docs/data/apps.json`，前端逻辑为 `docs/assets/app.js`，样式位于 `docs/assets/styles.css`。

仓库地址：https://github.com/VankerWu/iPhone-Duo-Apps

## 数据与版权

App 名称、品牌和图标属于各自权利人；目录整理以可核查证据为原则，禁止无证据宣称已适配。详情参考 [DATA_POLICY.md](DATA_POLICY.md)。

该项目与 Apple 及被收录应用开发者无官方关联。仓库原创代码依仓库内 LICENSE 授权；第三方内容不因此获得授权。

欢迎通过 [Issues](https://github.com/VankerWu/iPhone-Duo-Apps/issues) 提交适配反馈。
