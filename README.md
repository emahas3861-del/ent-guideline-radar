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

## 交互查询机器人

每周报告使用的是飞书“自定义群机器人”，它只能主动推送，不能接收你在群里的提问。
如果要做到“我在飞书里发 PMID、DOI 或主题，它自动查文献并回复总结”，需要另外配置一个飞书自建应用，并把本仓库部署成一个公开 Web 服务。

### 支持的提问范围

默认检索范围是耳鼻咽喉头颈外科大范围，不局限于甲状腺，包括但不限于：

- 鼻科、鼻窦炎、鼻息肉、过敏性鼻炎、鼻颅底
- 耳科、神经耳科、突发性耳聋、眩晕、听力学
- 咽喉、嗓音、吞咽、睡眠呼吸暂停
- 头颈肿瘤、甲状腺、涎腺、颈部肿块
- 儿童耳鼻咽喉、头颈外科围手术期与指南/共识

### 飞书里可以这样问

```text
PMID 40844370
DOI 10.1177/10507256251363120
查 最近 突发性耳聋 指南
查 鼻息肉 生物制剂 最新综述
查 头颈鳞癌 免疫治疗 指南
```

机器人会返回中文转述、PubMed 链接、DOI，以及能找到时的 PMC 开放全文链接。
付费全文不会绕过权限；如果没有开放全文，只能给原文链接和摘要级总结。

### 部署交互机器人

可以用 Render，也可以用腾讯云。仓库已提供两种部署入口：

- `render.yaml`：适合 Render Blueprint。
- `Dockerfile`：适合腾讯云云托管、容器服务或任何支持 Dockerfile 构建的 Web 服务。

#### 腾讯云部署要点

在腾讯云里创建一个能暴露公网 HTTPS 的 Web 服务，代码来源选择这个 GitHub 仓库，构建方式选择 Dockerfile。
服务需要监听环境变量 `PORT` 指定的端口；本仓库的 Dockerfile 已处理好。

环境变量填写：

| 环境变量 | 说明 |
|---|---|
| `DEEPSEEK_API_KEY` | DeepSeek API Key |
| `FEISHU_APP_ID` | 飞书自建应用 App ID |
| `FEISHU_APP_SECRET` | 飞书自建应用 App Secret |
| `FEISHU_VERIFICATION_TOKEN` | 飞书事件订阅 Verification Token |
| `NCBI_API_KEY` | NCBI API Key，可选 |

部署成功后，服务地址类似：

```text
https://你的腾讯云服务域名/feishu/events
```

#### Render 部署要点

1. 在 Render 新建 Blueprint 或 Web Service，连接这个 GitHub 仓库。
2. 启动命令使用：`uvicorn api.app:app --host 0.0.0.0 --port $PORT`。
3. 填入同样的环境变量。

Render 的事件订阅地址类似：

```text
https://你的服务名.onrender.com/feishu/events
```

### 飞书自建应用设置

1. 打开飞书开放平台，创建“企业自建应用”。
2. 开启机器人能力，并把应用添加到需要使用的群。
3. 在“事件订阅”里填写请求地址：`https://你的服务名.onrender.com/feishu/events`。
4. 配置 Verification Token，并填入部署平台的 `FEISHU_VERIFICATION_TOKEN`。
5. 订阅接收消息事件：`im.message.receive_v1`。
6. 给应用开通接收消息、发送消息相关权限，并发布/安装到当前企业。

第一版建议不要开启事件加密；如果你的飞书后台强制要求加密，再补充解密逻辑。
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
