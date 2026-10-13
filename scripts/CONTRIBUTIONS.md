# 贡献绿点维护

主页的个人网站入口下方展示 `assets/contributions.svg`，只更新 `CONTRIBUTIONS:START` / `CONTRIBUTIONS:END` 内的图片链接，保持其他正文和封面不变。

## 数据与日期

- `contributions.json` 中的 `start_date` 固定为 **2026-08-01**；结束日期使用 `Asia/Shanghai` 当天，继续按月向后显示。
- 数据直接读取 [GitHub GraphQL contributionCalendar](https://docs.github.com/en/graphql/reference/users#contributioncalendar)：每天的贡献次数和等级均来自 GitHub，格子日期沿用 GitHub 的 UTC 日期。
- 按自然半年排图段，跨年后继续追加，保留八月以来的历史，避免月份越多方块越小。
- 从现有公开贡献数据读取，不查询私有仓库名称或代码。数据保存在 `assets/contributions-data.json`，不包含令牌。
- API 错误、总数不符或缺少日期时保留上一张成功图片，不能把抓取失败画成零贡献。

## 自动更新

`Sync contribution calendar` 每 **5 分钟**检查一次，并支持手动运行；图片或日期范围有变化才提交。使用 GitHub Actions 自带的令牌，不需要新增个人令牌或外部服务。SVG 的内容哈希写入主页图片地址，数据变化时刷新图片缓存。

这不是逐秒推送。GitHub 数据本身可能延迟，Actions 排队或主页图片缓存也可能造成等待。[GitHub 的定时任务说明](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)规定最短间隔为 5 分钟，繁忙时可能延迟。

## 本地验证与手动同步

```sh
python3 -m unittest discover -s tests -p 'test_*contributions*.py' -v
python3 scripts/sync_contributions.py
gh workflow run sync-contributions.yml --repo 17lijunyi/17lijunyi
```

在线抓取使用 GitHub CLI（Actions 运行环境已预装）。本地可通过 `gh auth login` 既有授权读取公开数据；也可使用 `GH_TOKEN`。离线重建可传 `--data-json` 指定保存的 GraphQL 响应或包含 `days` 的数据文件，配合 `--through YYYY-MM-DD` 指定同样的结束日。

原生 SVG 由 `scripts/contributions_card.py` 绘制，沿用个人网站入口的浅色终端、蓝色提示字、窗口三色点和绿色贡献格。无需重新生成插画。
