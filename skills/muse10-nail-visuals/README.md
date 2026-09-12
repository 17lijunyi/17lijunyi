# Muse10 美甲作品展示

将一张或多张美甲参考照片，制作成同一套作品的商品视觉与交互预览：

**参考照片 → 十片陈列母版 → 同款双手佩戴 → 局部特写 → 可交互作品预览**

先核对十片母版，再以它为依据生成其他视角，保持甲型、颜色、材质、装饰和左右手指位一致。默认两排各五片、约 4:5 竖幅、灰蓝至银白渐变背景；新作品沿用用户照片的设计，不套用示例款式。AI 重绘可能产生细节差异，需要逐张检查。

| 十片陈列母版 | 同款双手佩戴 | 局部特写 |
| --- | --- | --- |
| ![十片陈列母版](assets/examples/master.jpg) | ![同款双手佩戴](assets/examples/wear.jpg) | ![局部特写](assets/examples/detail.jpg) |

以上为花园款 AI 效果示例。三张图是同一套作品的不同视角。

## 安装与使用

1. 下载或克隆本 GitHub 仓库。
2. 将仓库中的 `skills/muse10-nail-visuals` 整个文件夹复制到个人技能目录 `~/.codex/skills/`，保留其子目录。
3. 在 Codex 上传参考照片并调用：

> 使用 $muse10-nail-visuals，根据我上传的照片制作准确十片陈列、同款双手佩戴和局部特写，再做可交互作品预览，先不修改网站。

可补充必须保留与绝对不要的元素、背景或甲型要求。默认只制作独立预览；网站修改、部署或接入 AI 服务需按当次任务要求另行实施。

## 预览交互

- 默认显示十片陈列；鼠标移入临时显示佩戴图，移出恢复。
- 点击箭头或使用键盘左右键水平换图；手动翻页后保留当前图片。
- 手机支持横向滑动，保持纵向滚动；点击作品图或名称进入大图，返回或按 Escape 退出。
- 一套作品对应一个卡片，多套作品采用三列布局。

## 环境与打包

完整流程需要支持内置图像生成及 `visualize` 的 Codex 环境，并按当前 `imagegen`、`visualize` 技能执行。仅安装本技能不会自动提供图像模型或这些环境能力。

`scripts/build_preview.py` 使用 Python 3 标准库，将已经生成的本地 PNG、JPEG、WebP 或 GIF 嵌入 HTML 片段，不联网、不生成图片，也不将网页上线。示例命令：

```bash
python3 ~/.codex/skills/muse10-nail-visuals/scripts/build_preview.py \
  --manifest ~/.codex/skills/muse10-nail-visuals/assets/examples/gallery.json \
  --output ./muse10-preview.html
```

输出文件必须尚不存在，且片段小于 1 MB。替换示例清单中的图片即可打包自己的作品；相对图片路径以清单所在目录为准。

图库模板依赖宿主提供的全局 `lucide` 图标对象，未自行加载该库。输出主要用于 `visualize` 对话预览；直接作为普通网页打开时，宿主缺失会导致箭头等图标不显示。HTML 文件本身不等于公开网址或微信分享链接。

流程与质量检查见 [SKILL.md](SKILL.md)，提示词见 [references/prompts.md](references/prompts.md)，清单格式与交互规则见 [references/gallery.md](references/gallery.md)。
