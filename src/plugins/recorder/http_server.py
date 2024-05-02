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

            self.server.output.put(data)
            self.send_response(200)
            self.end_headers()
        except Exception as e:
            self.send_response(204)
            self.end_headers()
            self.wfile.write(bytes(str(e), "utf-8"))


class HttpServer(socketserver.TCPServer):

    def __init__(self, server_address, Handler, output):
        socketserver.TCPServer.__init__(self, server_address, Handler)
        self.output = output


class HttpServerProcess(Process):

    def __init__(self, ip, port, output):
        super().__init__()
        self.ip = ip
        self.port = port
        self.output = output

    def run(self):
        with HttpServer((self.ip, self.port), Handler, self.output) as httpd:
            httpd.serve_forever()
