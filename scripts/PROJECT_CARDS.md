# 项目卡片维护

主页的个人网站横幅与正文手动维护；只有 `PROJECTS:START` / `PROJECTS:END` 之间由脚本更新。卡片 SVG 和 `PROJECTS.md` 均自动生成，不要直接编辑。

## 展示规则

- `projects.json` 中的 `featured` 固定优先；其余按 GitHub `updated_at`（技能按目录最后提交时间）倒序排列。首页最多 6 张，有几个展示几个，不放空卡片。
- `PROJECTS.md` 包含全部符合条件的项目，包括未进入首页的项目。
- 只展示账号自己的公开、非 Fork、未归档仓库；主页仓库和已在顶部展示的个人网站仓库默认排除。
- 本仓库 `skills/*/SKILL.md` 配合 `agents/openai.yaml` 的 `display_name`、`short_description` 自动形成技能卡片；不会把主页仓库的 Star/Fork 数当作技能数据。
- 新技能需要提交上述两个元数据字段。技能内容只作为文本读取，不执行。
- 仓库标题默认使用仓库名，简介、语言、Star、Fork 来自 API。`overrides` 可设置中文标题或固定中文简介；被覆盖的字段以后需在配置中维护。

## 更新

GitHub Actions 每 6 小时运行一次（北京时间 02:23、08:23、14:23、20:23，实际运行可能排队延迟）。修改配置、脚本或技能会触发更新。其他仓库的新建、代码上传或简介修改由下一次定时任务发现，不会直接触发本仓库工作流。

可随时在 Actions → Sync project cards → Run workflow 手动同步，或运行：

```sh
gh workflow run sync-projects.yml --repo 17lijunyi/17lijunyi
```

脚本使用工作流自带的令牌，只需本仓库 contents: write，无需另存个人令牌。失败不会发布半成品；数据未变时不提交。长标题或简介仅在图片中截断，完整文本在项目目录和图片替代文本中保留。每张卡片使用内容版本号刷新图片缓存，并提供明暗两种主题。

GitHub 可能在公开仓库连续 60 天无活动后停用定时工作流；届时在 Actions 中重新启用即可。

本地检查：

```sh
python3 -m unittest discover -s tests -v
python3 scripts/sync_projects.py
```
