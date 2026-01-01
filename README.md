🚀 Serv00/CT8 自动保号脚本配置指南
1. Fork 仓库
点击页面右上角的 Fork 按钮，将本仓库克隆到你的 GitHub 账户下。

2. 配置 Secrets
进入你 Fork 后的仓库，依次点击 Settings -> Secrets and variables -> Actions -> New repository secret，添加以下 3 个变量：

ACCOUNTS_JSON

说明: 存放账号信息的 JSON 数据。

示例值:

JSON

[
  {"username": "账号1", "password": "密码1", "panel": "panel6.serv00.com"},
  {"username": "账号2", "password": "密码2", "panel": "panel.ct8.pl"}
]
TELEGRAM_BOT_TOKEN

说明: Telegram 机器人的 API Token。

获取: 在 Telegram 中联系 @BotFather 创建机器人获取。

TELEGRAM_CHAT_ID

说明: 你的 Telegram Chat ID。

获取: 向你的 Bot 发送任意消息，然后访问 https://api.telegram.org/bot<你的Token>/getUpdates 查看返回数据中的 id 字段。

3. 启动 GitHub Actions
进入仓库的 Actions 页面。

点击 I understand my workflows, go ahead and enable them (或 Enable GitHub Actions) 激活。

脚本将按照预设时间自动运行，你也可以在 Actions 页面手动触发运行。

⚠️ 注意事项
安全第一: Secrets 里的信息非常敏感，请勿将账号密码直接写入代码文件或公开分享。

管理配置: 如需修改账号或 Token，直接在 Secrets 页面更新对应变量即可。

🌟 觉得好用请点个 Star 支持一下！
