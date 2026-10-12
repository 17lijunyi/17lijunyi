# 项目图片封面

使用内置 image_gen 制作于 2026-10-12。六张均为 2172 × 724，主页保持每张 49% 宽、两列三行与现有项目顺序。

角色使用作者提供的白发、口罩、发光眼睛与灰白卫衣 IP；角色保持黑白灰，道具和场景保留彩色。App 使用各自当前图标，Skill 使用工具箱与技能卡片。

- [Foundry](foundry.png)：双手托起玻璃 F 图标。
- [AI 产品简历修改](ai-product-resume-edit.png)：从工具箱取出简历卡片并修改。
- [Orbi](orbi.png)：骑上粉色毛绒星球并挥手。
- [简励](jianli.png)：擦亮 JL 图标。
- [悬浮岛](xuanfudao.png)：在玻璃胶囊上滑行。
- [OvO](ovo.png)：坐在图标上交换翻译卡片。

[完整提示词及 OvO 构图修正](prompts.json)。生成器通过 projects.json 的 cover 字段使用这些图片，缓存版本取自文件内容哈希；定时同步不会覆盖图片设计。

OvO 与悬浮岛独立仓库的 README 顶部封面使用同一份最终图片。原始生成文件保留在 Codex 的 generated_images 中。
