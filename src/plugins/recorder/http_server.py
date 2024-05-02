from multiprocessing import Process
from http.server import CGIHTTPRequestHandler
import socketserver
import json
import os


class Handler(CGIHTTPRequestHandler):
    def do_POST(self):
        try:
            data = json.loads(bytes.decode(self.rfile.read(int(self.headers.get("Content-Length")))))

            if data['EventType'] != 'FileClosed':
                raise TypeError("Event not supported")

            relative_path:str = data.get('EventData', {}).get('RelativePath', None)

            if relative_path in self.server.uploading:
                raise OSError("File already uploaded")

            rclone_bin = self.server.reclone_bin

            if not os.path.exists(rclone_bin):
                raise FileNotFoundError("Reclone bin not found")

            with open(self.server.config_file, "r", encoding="utf-8") as f:
                config = json.load(f)

            streamer = relative_path.partition('/')[0]
            filename = relative_path.partition('/')[2]

            if streamer not in config['record_list']:
                raise FileNotFoundError("Config not found")

            streamer_config = config['record_list'][streamer]

            if streamer_config['rec'] != 'bili_rec':
                raise TypeError("Record not supported")

            self.server.uploading[relative_path] = True

            file_path = os.path.join(self.server.root_path, streamer, filename)
            os.rename(file_path, file_path.replace(" ", "_"))
            file_path = file_path.replace(" ", "_")

            cmds = [rclone_bin, 'copyto', f"{file_path}",
                    f"{streamer_config['upload_to']}/{streamer}"]

            os.system(' '.join(cmd for cmd in cmds))

            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"{\"Result\": \"Success\" }")
        except Exception as e:
            self.send_response(204)
            self.end_headers()
            self.wfile.write(bytes(str(e), "utf-8"))


class HttpServer(socketserver.TCPServer):

    def __init__(self, server_address, Handler, reclone_bin, config_file, root_path):
        socketserver.TCPServer.__init__(self, server_address, Handler)
        self.reclone_bin = reclone_bin
        self.config_file = config_file
        self.uploading = {}
        self.root_path = root_path


class HttpServerProcess(Process):

    def __init__(self, ip, port, reclone_bin, config_file, root_path):
        super().__init__()
        self.ip = ip
        self.port = port
        self.reclone_bin = reclone_bin
        self.config_file = config_file
        self.root_path = root_path

    def run(self):
        with HttpServer((self.ip, self.port), Handler, self.reclone_bin, self.config_file, self.root_path) as httpd:
            httpd.serve_forever()
