# -*- coding: utf-8 -*-
from bridge.context import *
from bridge.reply import *
from channel.chat_channel import ChatChannel
from common.log import logger
from common.singleton import singleton
from config import conf
from channel.wechat_wxhelper.utils.api import WXAPIBot
from channel.wechat_wxhelper.wxhelper_message import WXHelperMessage
from common.time_check import time_checker
import tempfile, os, requests, uuid

# from channel.wechat.wechat_message import *

# # wxhelper的配置
# "wxhelper_wxaddr": "http://127.0.0.1:19088/", # 注入微信后API的地址,
# "wxhelper_hookmsg_host": "127.0.0.1", # 注入微信后监听消息的地址
# "wxhelper_hookmsg_port": "8000",  # 注入微信后监听消息的端口


@singleton
class WXHelperChannel(ChatChannel):
    NOT_SUPPORT_REPLYTYPE = [ReplyType.VOICE]

    def __init__(self):
        super().__init__()
        # wxhelper的API监听地址
        self.wx_addr = conf().get("wxhelper_wxaddr", "http://127.0.0.1:19088/")
        self.wxapibot = WXAPIBot(self.wx_addr)

        # message hook地址
        self.hook_host = conf().get("wxhelper_hookmsg_host", "127.0.0.1")
        self.hook_port = int(conf().get("wxhelper_hookmsg_port", 8000))

        # 用来保存图片等文件的临时目录
        self.tmp_dir = os.path.join(tempfile.gettempdir(), "wxhelper")

    def startup(self):
        # TODO :1.后续添加自动注入并启动微信
        # TODO :2.定时任务
        # 启动listener监听hook msg端口，并且注册处理函数
        from channel.wechat_wxhelper.wxhelper_msgserver import WXBotTCPHandler, WXBotTCPServer

        # 保证临时文件夹存在
        if not os.path.exists(self.tmp_dir):
            os.makedirs(self.tmp_dir)
        # 监听的是0.0.0.0:hook_port
        hook_host_listen = conf().get("wxhelper_hookmsg_host_listen", self.hook_host)
        self.hookmsg_server = WXBotTCPServer((hook_host_listen, self.hook_port), WXBotTCPHandler)
        # 注册处理函数
        self.hookmsg_server.register_callback(self.handle_msg)
        # 调用API设置hook messsage server地址
        self.wxapibot.hook_msg(enablehttp="0", hook_ip=self.hook_host, hook_port=self.hook_port)
        # 启动服务器
        logger.info(f"Start WXHelper server, listen: tcp://{hook_host_listen}:{self.hook_port}")
        self.hookmsg_server.run()

    def handle_msg(self, msg: dict):
        fromuser = msg.get("fromUser")
        fromgroup = msg.get("fromGroup")
        isgroup = fromgroup != fromuser
        try:
            wxhelper_cmsg = WXHelperMessage(self.wxapibot, msg, is_group=isgroup)
        except NotImplementedError as e:
            logger.debug("[WXHelper] " + str(e))
            return {"message": "fail"}

        # 过滤自身发送了内容
        if wxhelper_cmsg.isSendMsg:
            pass
        # 群聊
        elif wxhelper_cmsg.is_group:
            self.handle_group(wxhelper_cmsg)
        # 私聊
        else:
            self.handle_single(wxhelper_cmsg)

        # 其余暂不处理
        return {"message": "success"}

    @time_checker
    def handle_single(self, cmsg: WXHelperMessage):
        """
        处理个人私聊信息
        """
        user_white_list = conf().get("wxhelper_user_white_list", [])
        # 白名单过滤
        # 排除掉自身的发送的消息
        if (cmsg.actual_user_nickname not in user_white_list) or (cmsg.actual_user_id == cmsg.to_user_id):
            return

        # 处理文本内容
        context = None
        if cmsg.ctype == ContextType.TEXT:
            logger.debug(f"[WXHelper] receive text msg: {cmsg.content}")
            context = self._compose_context(cmsg.ctype, cmsg.content, isgroup=False, msg=cmsg)
            # context = self._compose_context(ContextType.TEXT, con, wxhelper_cmsg)
        elif cmsg.ctype == ContextType.PATPAT:
            logger.debug(f"[WXHelper] receive PATPAT from user: {cmsg.actual_user_nickname}")
            context = self._compose_context(cmsg.ctype, cmsg.content, isgroup=False, msg=cmsg)
        if context:
            self.produce(context)

    @time_checker
    def handle_group(self, cmsg: WXHelperMessage):
        """
        处理群聊信息
        """
        context = None
        patpat_msg = f'"{cmsg.actual_user_nickname}" 拍了拍我'
        if cmsg.ctype == ContextType.TEXT:
            logger.debug(f"[WXHelper] receive text for group msg: {cmsg.content}")
            context = self._compose_context(cmsg.ctype, cmsg.content, isgroup=True, msg=cmsg)
            # context = self._compose_context(ContextType.TEXT, con, wxhelper_cmsg)
        elif cmsg.ctype == ContextType.PATPAT and cmsg.content.startswith(patpat_msg):
            logger.debug(f"[WXHelper] receive PATPAT from group user: {cmsg.actual_user_nickname}")
            context = self._compose_context(cmsg.ctype, cmsg.content, isgroup=True, msg=cmsg)
        if context:
            self.produce(context)

    def send(self, reply: Reply, context: Context):
        receiver = context["receiver"]
        if reply.type == ReplyType.TEXT:
            logger.info("[WXHelper] sendMsg={}, receiver={}".format(reply, receiver))
            self.wxapibot.send_text_msg(msg=reply.content, wxid=receiver)
            # if context["isgroup"]:
            #     # 发送群聊目前不使用at人回复的方式
            #     self.wxapibot.send_text_msg(msg=reply.content ,wxid=receiver)
            # else:
            #     self.wxapibot.send_text_msg(msg=reply.content ,wxid=receiver)
        elif reply.type == ReplyType.ERROR or reply.type == ReplyType.INFO:
            # 适配插件相关内容
            logger.info("[WXHelper] send system reply={}, receiver={}".format(reply, receiver))
            self.wxapibot.send_text_msg(msg=reply.content, wxid=receiver)
        elif reply.type == ReplyType.IMAGE_URL:
            img_url = reply.content
            logger.info("[WXHelper] send imageurl={}, receiver={}".format(reply, receiver))
            img_path = os.path.join(self.tmp_dir, uuid.uuid4().hex + ".jpg")
            response = requests.get(img_url)
            with open(img_path, "wb") as f:
                f.write(response.content)
            self.wxapibot.send_img(filepath=img_path, wxid=receiver)
            os.remove(img_path)
        elif reply.type == ReplyType.IMAGE:
            img_path = reply.content
            logger.info("[WXHelper] sendimage={}, receiver={}".format(reply, receiver))
            self.wxapibot.send_img(filepath=img_path, wxid=receiver)
