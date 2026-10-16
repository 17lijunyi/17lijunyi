# 项目图片封面

原始插画使用内置 image_gen 制作于 2026-10-12，2026-10-13 补齐并修正。首批共 11 张原画，尺寸 2172 × 724。

2026-10-15，Orbi 更新为用户从十个腿部修正版中选定的第 10 版：双腿向右轻摆，补全大腿、膝盖与小腿的连接。用户确认的完整窗口图为 1977 × 795，直接保存为 `orbi-window.png`；[生成提示词与版本记录](orbi-selected-20261015.json)。`orbi.png` 保留为早期插画存档，`projects.json` 不再将它配置为 Orbi 的重建输入，避免批量重建窗口时恢复旧腿部。

2026-10-13 添加代码绘制的窗口外框与分类顶栏。主页和全部项目页使用 `*-window.png`（2252 × 906），每张 49% 宽、两列连续排列，顺序为产品 → Skills → 文档 → 其他。分类写在各张卡片的顶栏，移除卡片外的分组标题和图下说明；整张图片保留项目链接。分类切换不另起一行，仅最后一个奇数项目可能单独占一行。

角色使用作者提供的白发、口罩、发光眼睛与灰白卫衣 IP；角色保持黑白灰，道具和场景保留彩色。App 使用各自当前图标，Skill 使用工具箱与技能卡片。

## 产品

- [Foundry](foundry.png)：双手托起玻璃 F 图标。
- [PE Studio](pe-studio-window.png)：灰白 IP 持橙色笔比较 A/B/C 提示词卡片，与银色 P 图标互动；突出三模型并行优化与随机盲测。2026-10-15 使用内置 image_gen 制作原画，并由统一模板加上青绿色产品窗口顶栏。[生成提示词](pe-studio-generation.json)。
- [Orbi](orbi-window.png)：保留骑粉色毛绒星球、挥手的坐姿，双腿向右轻摆，腿部连接自然。
- [简励](jianli.png)：擦亮 JL 图标。
- [悬浮岛](xuanfudao.png)：在玻璃胶囊上滑行。
- [OvO](ovo.png)：坐在图标上交换翻译卡片。
- [FrameFlow](frameflow.png)：单膝跪地，用摄像机拍摄场记板。

## Skills

- [AI 产品简历修改](ai-product-resume-edit.png)：从工具箱取出简历卡片并修改。
- [产品证据拆解](product-evidence-deconstruction.png)：趴地用放大镜追踪四层证据卡片。
- [Muse10 款式生成](muse10-nail-visuals.png)：侧身踏箱挥笔，画出十片款式阵列。

三张封面均明确写有 Skills。

## 文档

- [产品蓝图](product-blueprint-window.png)：灰白 IP 踏在双层梯台上，将架构模块拼入蓝图；突出需求拆解、架构选型与代码骨架。[生成提示词与记录](product-blueprint-generation.json)。
- [技术栈手册](tech-stack-handbook-window.png)：灰白 IP 双手捧读蓝色手册，旁边配有彩色书堆与前端、数据库和云端模块，展示从想法到上线的开发流程。[生成提示词与记录](tech-stack-handbook-generation.json)。
- [看山 KB](kanshan-kb.png)：半躺在巨大的书页上阅读，窗口顶栏标明文档。

## 其他

- [每日 AI 新闻](daily-ai-news.png)：迈步拉着报纸车前进，窗口顶栏标明其他。

[首批提示词及 OvO 构图修正](prompts.json) · [首轮补齐与分类标识记录](prompts-20261013.json) · [动作差异化与 Orbi 腿部局部修复完整提示词](prompts-20261013-motion.json)。原画文件不变，窗口版直接复制每个原画像素，并在写出后逐像素验证；不缩放、不重新生成角色或道具。

窗口外框由 [build_cover_windows.mjs](../../scripts/build_cover_windows.mjs) 重建，需要 Node.js、`sharp` 和 `pngjs`。在仓库根目录运行：

```sh
node scripts/build_cover_windows.mjs
```

可用 `--modules-dir /path/to/node_modules` 指定已有依赖目录，用 `--only repo:Foundry` 重建单张。`projects.json` 的 `artwork` 指向原画，`cover` 指向窗口版，`category` 决定顶栏标签，`window_theme` 决定外框淡色。修改原画或这些窗口配置后先重建窗口，再运行 `python3 scripts/sync_projects.py`。已确认的 Orbi 完整窗口图直接使用，批量重建跳过该图。

同步脚本通过 `cover` 使用窗口版图片，缓存版本取自文件内容哈希；定时同步不会重新绘制或覆盖图片设计。

OvO 与悬浮岛独立仓库的 README 顶部封面使用同一份最终图片。原始生成文件保留在 Codex 的 generated_images 中。
