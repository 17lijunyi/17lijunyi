# 项目卡片维护

项目同步只更新 `PROJECTS:START` / `PROJECTS:END` 之间的内容。个人网站入口横幅由[贡献同步](CONTRIBUTIONS.md)维护，其他正文手动维护。备用卡片 SVG 和 `PROJECTS.md` 均自动生成，不要直接编辑；已设计的图片封面保留在 `assets/project-covers/`。

## 展示规则

- 当前配置 `collapsible_categories: true`，主页和 `PROJECTS.md` 均按 ⭐ 精选项目 → 📚 知识文档 → 🧰 Skills 显示三个独立模块，每个模块有自己的二级标题和折叠封面，默认全部收起。点击分类封面可展开、收起，各栏目互不影响；不显示项目数量或图下提示，展开后保留可点击的双列项目封面。
- 折叠栏目始终收录全部符合条件的项目，不受 `limit` 限制。原来的 `repository`（其他）统一并入文档；未来未指定分类的新仓库也归入文档，不会丢失。
- `category_covers` 必须提供 `product`、`document`、`skill` 三张分类封面，路径限制为仓库内 `assets/project-covers/` 的 PNG、JPEG 或 WebP；缺图、路径越界或配置错误时，保留之前全部生成文件。当前使用高清 PNG，分类封面宽度为内容区的 100%，随容器缩放，文件内容变化会刷新缓存。
- 栏目使用 GitHub 原生 `details` / `summary`，无脚本和自定义 CSS。分类图直接放在 `summary` 的 `picture` 内，避免 GitHub 自动把图片变成打开原图的链接；不要移除这层标签或给分类图额外加链接。不加 `open` 或共享 `name` 属性，确保默认收起、独立展开。GitHub 原生折叠箭头由平台显示，README 无法通过自定义 CSS 可靠隐藏。
- 同类中 `featured` 固定优先，其余按 GitHub `updated_at`（技能按目录最后提交时间）倒序排列。仓库的 `overrides.category` 可为 `product`、`skill`、`document`、`repository`；独立技能仓库需显式设置为 `skill`，本仓库技能目录自动归为 Skills。
- 关闭 `collapsible_categories` 可恢复原来的展示模式：`group_by_category: true` 按产品 → Skills → 文档 → 其他排序；`compact_cards: true` 显示不另起分类行的连续双列图片墙。旧模式的 `show_all: true` 展示全部，关闭时首页使用 `limit`，项目目录仍展示全部。
- 只展示账号自己的公开、非 Fork、未归档仓库；主页仓库和已在顶部展示的个人网站仓库默认排除。
- 本仓库 `skills/*/SKILL.md` 配合 `agents/openai.yaml` 的 `display_name`、`short_description` 自动形成技能卡片；不会把主页仓库的 Star/Fork 数当作技能数据。
- 新技能需要提交上述两个元数据字段。技能内容只作为文本读取，不执行。
- 仓库标题默认使用仓库名，简介、语言、Star、Fork 来自 API。`overrides` 可设置中文标题或固定中文简介；被覆盖的字段以后需在配置中维护。
- `overrides.cover` 指定窗口封面；窗口绘制配置、原画像素保留方式与重建命令见 [封面维护](../assets/project-covers/README.md)。新增项目没有定制插画时先显示 SVG 备用卡片，不会被遗漏。
- 独立仓库也可用 `overrides.cover_url` 引用该仓库 `main` 分支上的 HTTPS `raw.githubusercontent.com` 图片，不复制资产。它与 `cover` 不能同时设置；缓存版本随仓库更新时间变化。

## 更新

GitHub Actions 每 6 小时运行一次（北京时间 02:23、08:23、14:23、20:23，实际运行可能排队延迟）。修改配置、脚本或技能会触发更新。其他仓库的新建、代码上传或简介修改由下一次定时任务发现，不会直接触发本仓库工作流。

可随时在 Actions → Sync project cards → Run workflow 手动同步，或运行：

```sh
gh workflow run sync-projects.yml --repo 17lijunyi/17lijunyi
```

脚本使用工作流自带的令牌，只需本仓库 contents: write，无需另存个人令牌。失败不会发布半成品；数据未变时不提交。完整标题和简介在图片替代文本中保留。每张卡片使用内容版本号刷新图片缓存；备用 SVG 提供明暗两种主题，定制插画按设计原样展示。

GitHub 可能在公开仓库连续 60 天无活动后停用定时工作流；届时在 Actions 中重新启用即可。

本地检查：

```sh
python3 -m unittest discover -s tests -v
python3 scripts/sync_projects.py
```
