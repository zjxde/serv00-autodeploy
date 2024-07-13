serv00与ct8自动化部署启动，保活，并且可发送消息到Telegram
利用github Action以及python脚本实现
🙏🙏🙏点个Star！！Star！！Star！！
将代码fork到你的仓库并运行的操作步骤
(一). Fork 仓库
    1、访问原始仓库页面： 打开你想要 fork 的 GitHub 仓库页面。
    2、Fork 仓库 点击页面右上角的 "Fork" 按钮，将仓库 fork 到你的 GitHub 账户下。
(二). 设置 GitHub Secrets
    1、创建 Telegram Bot
        在 Telegram 中找到 @BotFather，创建一个新 Bot，并获取 API Token。 
        获取到你的 Chat ID 方法一，在一休技术交流群里发送/id@KinhRoBot获取，返回用户信息中的ID就是Chat ID
        获取到你的 Chat ID 方法二，可以通过向 Bot 发送一条消息，然后访问 https://api.telegram.org/bot<your_bot_token>/getUpdates 找到 Chat ID
(三)配置 GitHub Secrets
    1、转到你 fork 的仓库页面。
    2、点击 Settings，然后在左侧菜单中选择 Secrets。
    3、添加以下 Secrets：
    4、user_info.json: 包含账号信息的 JSON 数据。例如：
    {
        "username": "【用户名,必填】",
        "password": "【密码,必填】",
        "domain": "【域名，必填】",
        "basepath": "【部署路径，可以不填】",
        "pannelnum": 6, 【serv00机器号，必填】
        "uuid_ports": [
        {"uuid": "cbbc53be-7436-4418-bbc7-0243d057bf7e", "port": 0},【可修改自己的uuid值，也可以不修改,port值默认即可】
        {"uuid": "5ccac840-3c3b-11ef-b292-005056c00008", "port": 0},
        {"uuid": "6adcae4e-16cc-443d-98c0-49f5c5dd46b9", "port": 0}
        ],
        "env_config": {
        "reset": 1, 【是否需要重置环境】
        "node_num": 3,【开启节点个数，由于节点serv00端口限制，最多可设3个】
        "outo_npm_install": 1,【默认即可】
        "code_source_url": "git clone http://github.com/zjxde/serv00-ws",
        "send_tg": 0,【是否需要发送节点url到telegram】
        "kill_pid_path": "serv00",【默认即可】
        "nodejs_name": "index",【默认即可】
        "proxies": ["test1.com","test2.com"]【默认即可】
        },
        "tg_config": {
        "tg_bot_token": "【申请tg机器人的token】",
        "tg_chat_id": "【Chat ID】"
        }
    }
(三). 启动 GitHub Actions
    1、配置 GitHub Actions
        》在你的 fork 仓库中，进入 Actions 页面。
        》如果 Actions 没有自动启用，点击 Enable GitHub Actions 按钮以激活它。
    2、运行工作流 
        》GitHub Actions 将会根据你设置的定时任务（例如每三天一次）自动运行脚本。
        》如果需要手动触发，可以在 Actions 页面手动运行工作流。
(四).注意事项
    1、保密性: Secrets 是敏感信息，请确保不要将它们泄露到公共代码库或未授权的人员。
    2、更新和删除: 如果需要更新或删除 Secrets，可以通过仓库的 Secrets 页面进行管理。
    3、通过以上步骤，你就可以成功将代码 fork 到你的仓库下并运行它了。如果需要进一步的帮助或有其他问题，请随时告知！