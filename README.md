# JiBot(鸡器人)

## Overview  环境依赖
本bot基于[NoneBot2](https://github.com/nonebot/nonebot2)与[go-cqhttp](https://github.com/Mrs4s/go-cqhttp)开发，部分插件使用现有的开源插件，配置启动需要安装以下环境
   * NoneBot2主框架，可以通过`pip`等工具安装（详见文档[NoneBot2](https://v2.nonebot.dev/docs/start/installation)）
      ```
      pip install nb-cli
      ```
   * 协议适配器，可以通过NoneBot2的脚手架`nb-cli`进行安装（详见文档[OneBot v11](https://adapter-onebot.netlify.app/docs/guide/installation)）
      ```
      nb adapter install nonebot-adpater-onebot
      ```
   * 定时任务需要额外安装一项计时器,可以通过NoneBot2的脚手架`nb-cli`进行安装(详见文档[NoneBot2](https://v2.nonebot.dev/docs/advanced/scheduler))
      ```
      nb plugin install nonebot_plugin_apscheduler
      ```
   * 安装协议端go-cqhttp，下载对应平台build的文件解压即可(详见[go-cqhttp release](https://github.com/Mrs4s/go-cqhttp/releases))
   
   * 根据插件情况分别需要一些额外依赖

      * wishlist_listener: 使用`requests`同步直接请求html文件
         ```
         pip install requests
         ```
      * user_translator: 翻译的请求使用`aiohttp`进行异步请求，文本处理时需要使用`emoji`进行替换处理
         ```
         pip install aiohttp
         pip install emoji
         ```
      * plugin_status: 需要使用第三方库`psutil`查询服务器运行状态
         ```
         pip instal psutil
         ```
      * haruka_bot: 一大堆第三方依赖，使用`nb-cli`安装时会自动安装
         ```
         nb plugin install haruka_bot
         ```
         启动bot前需要在`.end.prod`中设置数据库保存的位置，建议和其他插件一样保存在./data目录的插件子目录下
         ```
         HARUKA_DIR="./data/haruka_bot"
         ```
         该插件源码保存在python包文件夹中，需要进行修改可以直接在包文件夹中修改，包路径查找示例如下
         ```
         >>> import haruka_bot
         >>> print(haruka_bot)
         <module 'haruka_bot' from '/usr/local/lib/python3.9/dist-packages/haruka_bot/__init__.py'>
         ```
      * plugin_twitter: 需要第三方库`selenium`及linux版`chrome/chromedriver`
         * selenium可使用pip安装 
            ```
            pip install selenium
            ```
         * chrome需要在google官网下载linux发行版并进行安装，过程中可能需要额外安装一些系统依赖，
            ```
            wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
            sudo dpkg -i google-chrome-stable_current_amd64.deb
            ```
            如果在安装chrome时缺少系统依赖导致失败，尝试以下命令安装缺少的依赖
            ```
            sudo apt --fix-broken install
            ```
         * chromedriver需要在[Chromedriver](https://chromedriver.storage.googleapis.com/index.html)额外下载并保存至PATH
## Function  主要功能
1. wishlist_listener: 自制插件，定时监听Amazon愿望单中物品变化情况并发送至指定群，老头快人一步
2. auto_translator: 自制插件，指定源语言与目标语言对特定用户的所有发言进行翻译，翻译结果将保留原文中的emoji及qq自带表情，翻译引擎使用腾讯TMT，每月免费额度对于轻度使用非常友好，请求时需要TC3-HMAC-SHA256签名，签名方法详见[Tencent TMT](https://cloud.tencent.com/document/product/551/30636)
3. manual_translator: 自制插件，指定目标语言进行翻译，翻译接口同上
3. nonebot_plugin_status: 已发布插件，远程查询服务器cpu·内存·硬盘等使用百分比，详见[status](https://github.com/cscs181/QQ-GitHub-Bot/tree/master/src/plugins/nonebot_plugin_status)
4. nonebot_plugin_manager: 已发布插件，对不同群的插件开启进行管理，详见[manager](https://github.com/nonepkg/nonebot-plugin-manager)
5. nonebot_plugin_twitter: 已发布插件，对关注的推特用户内容进行推送和翻译，修改自[ErikaBot](https://github.com/SlieFamily/ErikaBot)
6. haruka_bot: 已发布插件，对关注的B站用户动态，直播等内容进行推送，修改自[Harukabot](https://github.com/SK-415/HarukaBot)
## Guide  启用方法
1. 安装依赖，将本仓库克隆至本地后，在本文件目录内配置.env.prod。必须进行配置的项目
   ```
   SUPERUSERS=[str|int]   超级用户id，个别指令将限制为仅限超级用户使用

   ADMIN_GROUP=str|int    管理群，可以对bot进行全局管理—、控制以及测试

   API_SECRETID=str       腾讯云API的SecretID，必需。需要在腾讯云控制中心开启相应API权限

   API_SECRETKEY=str      腾讯云API的SecretKey，必需。需要在腾讯云控制中心开启相应API权限

   API_REGION=str         请求的地域，部分API将会有区域化数据。

   TRANSLATE_ENDPOINT=str 最终请求的域名，可以在TMT文档中查到位于不同物理位置的域名

   TWITTER_TOKEN=str      Twitter API Token，可以在Twitter developer页面进行申请
   ```
   其他可选配置项目参考各个插件文档

2. 在本文件目录运行nonebot
```
nb run
```
3. （可选）非海外服务器需要设置HTTP, HTTPS代理以请求Twitter及Amazon
4. （可选）将Jibot与go-cqhttps配置为systemd service并设置开机启动，需要后于network.target以及代理服务启动

## Doc  参考文档
See [NoneBot2](https://v2.nonebot.dev/)

See [go-cqhttp](https://docs.go-cqhttp.org/)

See [TMT文本翻译](https://cloud.tencent.com/document/api/551/15619)

See [Twitter_Developer_Platform](https://developer.twitter.com/en)

各个插件文档见`主要功能`部分