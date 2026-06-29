# 耳鼻咽喉头颈外科指南与文献雷达

每周自动检索耳鼻咽喉头颈外科相关的新指南、共识和重要文献，用 DeepSeek 转述成中文详细报告，并发送到飞书。

## 每周运行时间

GitHub Actions 使用 UTC 时间。当前配置为：

- 北京/上海时间：每周一 08:00
- GitHub cron：`0 0 * * 1`

## 需要配置的 GitHub Secrets

进入 GitHub 仓库页面：

`Settings` → `Secrets and variables` → `Actions` → `New repository secret`

添加：

| Secret 名称 | 说明 |
|---|---|
| `DEEPSEEK_API_KEY` | DeepSeek API Key |
| `FEISHU_WEBHOOK_URL` | 飞书群机器人 Webhook |
| `FEISHU_WEBHOOK_SECRET` | 飞书机器人签名密钥，可选但建议开启 |
| `NCBI_API_KEY` | NCBI API Key，可选 |

不要把任何 Key 写进代码或提交到 GitHub。

## 飞书 Webhook 怎么查看

在飞书里：

1. 打开要接收报告的群。
2. 点击右上角 `...` 或群设置。
3. 找到 `群机器人` / `机器人`。
4. 添加 `自定义机器人`。
5. 设置机器人名称，例如 `ENT文献雷达`。
6. 安全设置建议选择 `签名校验`，保存后会看到：
   - Webhook 地址：填到 `FEISHU_WEBHOOK_URL`
   - 签名密钥：填到 `FEISHU_WEBHOOK_SECRET`

## GitHub 仓库地址在哪里看

打开你的 GitHub 仓库网页，浏览器地址栏里的地址就是仓库地址，格式通常是：

```text
https://github.com/你的用户名/仓库名
```

如果你还没有仓库：

1. 登录 GitHub。
2. 点击右上角 `+` → `New repository`。
3. Repository name 可写：`ent-guideline-radar`。
4. 选择 Private 或 Public。
5. 创建后，把浏览器地址栏里的仓库地址发给我。

## 本地试运行

```powershell
$env:DEEPSEEK_API_KEY="你的新DeepSeek Key"
$env:FEISHU_WEBHOOK_URL="你的飞书Webhook"
$env:FEISHU_WEBHOOK_SECRET="你的飞书签名密钥"
python -m src.main
```

## 输出与去重

- `outputs/` 保存每期报告。
- `data/seen_items.json` 保存已经推送过的 PMID/DOI/链接。
- GitHub Actions 每次运行后会自动提交这些记录，避免下周重复推送。
