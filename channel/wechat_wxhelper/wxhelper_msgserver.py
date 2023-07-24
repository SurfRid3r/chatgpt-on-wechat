import socketserver
import threading
import json
from common.log import logger


class WXBotTCPHandler(socketserver.BaseRequestHandler):
    def handle(self):
        data = b""
        while True:
            recv_data = self.request.recv(1024)
            # if len(data) == 0 or data[-1] == 0xA:
            if not recv_data:
                break
            data += recv_data

        try:
            json_data = json.loads(data)
            logger.debug(f"[WXBotTCPHandler] Received message: {json_data}")

            self.server.callback(json_data)

        except Exception as e:
            logger.error(f"[WXBotTCPHandler] Error handling request: {e}")


class WXBotTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    def __init__(self, server_address, handler_class=WXBotTCPHandler):
        super().__init__(server_address, handler_class)
        self.callback = self.defalut_handle_data

    def register_callback(self, callback):
        """
        注册callback函数处理msg
        """
        self.callback = callback

    def run(self):
        if threading.current_thread() is threading.main_thread():
            self.serve_forever()
        else:
            self.run_in_thread()

    def run_in_thread(self):
        socket_server = threading.Thread(target=self.serve_forever)
        socket_server.setDaemon(True)
        socket_server.start()
        return socket_server.ident

    @staticmethod
    def defalut_handle_data(msg):
        print(f"[WXBotTCPServer] Received message: {msg}")
