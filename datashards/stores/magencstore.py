import http.server
import socketserver
from urllib.parse import urlparse, parse_qs

from .base import BaseStore, GetStore, PutStore, StoreError
from .memorystore import MemoryStore

memstore = MemoryStore()

class MagencStore(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        print(f"Request recieved: {self.path}")
        try:
            parsed = urlparse(self.path)
            query = parsed.query
            params = parse_qs(query)
            xt = params['xt'][0]
            result = memstore.get(xt)
        except KeyError:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(f'Shard Not Found'.encode())
            return
        except ValueError as err:
            self.send_response(400)
            self.wfile.write(f"Malformed request: {err}".encode())
            return
        except Exception as err:
            self.send_response(500)
            self.wfile.write(f"Server Error: {err}".encode())
            return
        self.send_response(200)
        self.send_header('Content-type', 'application/octet-stream')
        self.end_headers()
        self.wfile.write(result)

    def do_POST(self):
        #length = int(self.headers['Content-Length'])
        #content = self.rfile.read(length)
        content = self.rfile.read(32768)
        try:
            xt = memstore.put(content)
        except ValueError as err:
            self.send_response(400)
            self.wfile.write(f"Malformed request: {err}".encode())
        except Exception as err:
            self.send_response(500)
            self.wfile.write(f"Server Error: {err}".encode())
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(xt.encode())
