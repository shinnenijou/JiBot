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
   
   * 根据插件情况分别需要一些额外依赖: 

      * wishlist_listener: 使用`requests`同步直接请求html文件
         ```
         pip install requests
         ```
      * auto_translator: 翻译的请求使用`aiohttp`进行异步请求，文本处理时需要使用`emoji`进行替换处理
         ```
         pip install aiohttp
         pip install emoji
         ```
      * manual_translator: 同auto_translator

      * twitter: 需要第三方库`emoji`及`aiohttp`

      * bilibili: 需要使用第三方库`emoji`, `aiohttp`及`bilibili_api`所需要的一些其他依赖
      ```
      pip install bilibili_api
      ```

      * plugin_status: 需要使用第三方库`psutil`查询服务器运行状态
         ```
         pip instal psutil
         ```

## Function  主要功能
1. wishlist_listener: 自制插件，定时监听Amazon愿望单中物品变化情况并发送至指定群，老头快人一步
2. auto_translator: 自制插件，指定源语言与目标语言对特定用户的所有发言进行翻译，翻译结果将保留原文中的emoji及qq自带表情，翻译引擎使用腾讯TMT，每月免费额度对于轻度使用非常友好，请求时需要TC3-HMAC-SHA256签名，签名方法详见[Tencent TMT](https://cloud.tencent.com/document/product/551/30636)
3. manual_translator: 自制插件，指定目标语言进行翻译，翻译接口同上
4. twitter: 自制插件，对关注的推特用户内容进行推送和翻译, 保留图片，emoji，转推原文等信息
5. bilibili: 自制插件，对关注的bilibili主播动态, 视频发布, 直播等进行推送, 保留图片, emoji, 转发愿文等信息, 可以在群内直接回复评论某条最新动态(使用管理员账号)
6. nonebot_plugin_status: 已发布插件，远程查询服务器cpu·内存·硬盘等使用百分比，详见[status](https://github.com/cscs181/QQ-GitHub-Bot/tree/master/src/plugins/nonebot_plugin_status)
7. nonebot_plugin_manager: 已发布插件，对不同群的插件开启进行管理，详见[manager](https://github.com/nonepkg/nonebot-plugin-manager)
## Guide  启用方法
1. 安装依赖，将本仓库克隆至本地后，在本文件目录内配置.env.prod。必须进行配置的项目
   ```
   SUPERUSERS=[str|int]       超级用户id，个别指令将限制为仅限超级用户使用

   ADMIN_GROUP=str|int        管理群，可以对bot进行全局管理—、控制以及测试

   API_SECRETID=str           腾讯云API的SecretID，必需。需要在腾讯云控制中心开启相应API权限

   API_SECRETKEY=str          腾讯云API的SecretKey，必需。需要在腾讯云控制中心开启相应API权限

   API_REGION=str             请求的地域，部分API将会有区域化数据。

   TRANSLATE_ENDPOINT=str     最终请求的域名，可以在TMT文档中查到位于不同物理位置的域名

   TWITTER_TOKEN=str          Twitter API Token，可以在Twitter developer页面进行申请

   TWEET_LISTEN_INTERVAL=int  推特监听间隔，单位为秒

   TWEET_SOURCE=str           推特翻译源语言, 填入指定的语言缩写, 如'zh','ja','en'等，可以填'auto'自动选择
   
   TWEET_TARGET=str           推特翻译目标语言

   BILI_SESSDATA=str          BILIBILI账号cookie之一, 可以登陆后在浏览器开发者工具中查到
   
   BILI_JCT=str               BILIBILI账号cookie之一, 可以登陆后在浏览器开发者工具中查到
   
   BILI_BUVID3=str            BILIBILI账号cookie之一, 可以登陆后在浏览器开发者工具中查到
   
   BILI_SOURCE=               BILI动态翻译源语言
   
   BILI_TARGET=               BILI动态翻译目标语言
   
   DYNAMIC_COMMENT_EXPIRATION=int   动态评论功能的有效时间，超过这个时间的动态将无法评论，单位是秒
   
   DYNAMIC_LISTEN_INTERVAL=int      BILI动态监听的时间间隔, 单位是秒

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

See [bilibili_api](https://bili.moyu.moe/#/)

各个插件文档见`主要功能`部分