# JiBot(鸡器人)

## Overview： 环境依赖
本bot基于(https://github.com/nonebot/nonebot2 "NoneBot2")与(https://github.com/Mrs4s/go-cqhttp "go-cqhttp")开发，配置启动需要安装以下环境
1. NoneBot2主框架，可以通过pip等工具安装（详见文档(https://v2.nonebot.dev/docs/start/installation "NoneBot2")）
>pip install nb-cli
2. 协议适配器，可以通过NoneBot2的脚手架nb进行安装（详见文档(https://adapter-onebot.netlify.app/docs/guide/installation "OneBotv11")）
>nb adapter install nonebot-adpater-onebot
3. 定时任务需要额外安装一项计时器,可以通过NoneBot2的脚手架nb进行安装(详见文档(https://v2.nonebot.dev/docs/advanced/scheduler "NoneBot2"))
>nb plugin install nonebot_plugin_apscheduler
4. 根据插件情况分别需要一些额外依赖
wishlist_listener: requests
>pip install requests
user_translator: 由于翻译接口使用腾讯云API，需要安装腾讯云SDK方便请求（详见(https://cloud.tencent.com/document/sdk/Python "腾讯云API中心")）
>pip install --upgrade tencentcloud-sdk-python

## Function: 主要功能
1. wishlist_listener: 监听Amazon愿望单中物品变化情况并发送至指定群
2. user_translator: 指定源语言与目标语言对特定用户的所有发言进行翻译


## Guide： 启用方法
1. 安装依赖，将本仓库克隆至本地后，在本文件目录内配置.env.prod。必须进行配置的项目
>SUPERUSERS=[str|int] 超级用户id，个别指令将限制为仅限超级用户使用
>ADMIN_GROUP=str|int  管理群，可以对bot进行全局管理—、控制以及测试
>API_SECRETID=str     腾讯云API的SecretID，必需。需要在腾讯云控制中心开启相应API权限
>API_SECRETKEY=str    腾讯云API的SecretKey，必需。需要在腾讯云控制中心开启相应API权限
>API_REGION=str       请求的地域，部分API将会有区域化数据。

2. 在本文件目录运行bot
>nb run

## Documentation

See [Docs](https://v2.nonebot.dev/)
