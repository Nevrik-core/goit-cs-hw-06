import mimetypes
import socket
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from urllib.parse import urlparse, unquote_plus
from pymongo import MongoClient
from datetime import datetime


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# HTTP сервер
BASE_DIR = Path(__file__).resolve().parent
HTTP_PORT = 3000
HTTP_HOST = '0.0.0.0'

# Сокет сервер
SOCKET_HOST = '127.0.0.1'
SOCKET_PORT = 5000


MONGO_URI = 'mongodb://mongodb:27017/messages_db'
client = MongoClient(MONGO_URI)
db = client['messages_db']
collection = db['messages']


class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        router = urlparse(self.path).path
        match router:
            case "/":
                self.send_html("index.html")
            case "/message":
                self.send_html("message.html")
            case _:
                file = BASE_DIR.joinpath(router[1:])
                if file.exists():
                    self.send_static(file)
                else:
                    self.send_html("error.html", 404)


    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)


        try:
            # Відправлення даних на сокет-сервер
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client_socket:
                client_socket.sendto(post_data, (SOCKET_HOST, SOCKET_PORT))
            
            # Перенаправлення на головну сторінку
            self.send_response(302)
            self.send_header('Location', '/')
            self.end_headers()
        except Exception as e:
            logging.error(f"Error during POST request processing: {e}")
            self.send_error(500, "Internal Server Error")

    def send_html(self, filename, status=200):
        self.send_response(status)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        with open(filename, "rb") as f:
            self.wfile.write(f.read())

    def send_static(self, file, status=200):
        self.send_response(status)
        mimetype, _ = mimetypes.guess_type(file)
        self.send_header("Content-type", mimetype or "application/octet-stream")
        self.end_headers()
        with open(file, "rb") as f:
            self.wfile.write(f.read())

def run_http_server(server_class=HTTPServer, handler_class=SimpleHTTPRequestHandler):
    server_address = (HTTP_HOST, HTTP_PORT)
    httpd = server_class(server_address, handler_class)
    try:
        logging.info(f'HTTP server is starting at http://{HTTP_HOST}:{HTTP_PORT}')
        httpd.serve_forever()
    except Exception as e:
        logging.error(f'HTTP server error: {e}')
    finally:
        httpd.server_close()
        logging.info('HTTP server stopped')

def run_socket_server():
    
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as server_socket:
            server_socket.bind((SOCKET_HOST, SOCKET_PORT))
            logging.info(f"UDP Server listening on {(SOCKET_HOST, SOCKET_PORT)}")
            while True:
                data, addr = server_socket.recvfrom(1024)
                save_data(data)
    except Exception as e:
        logging.error(f'Socket server error: {e}')


def save_data(data):
    try:
        data = data.decode('utf-8')
        data_dict = {k: unquote_plus(v) for k, v in (x.split('=') for x in data.split('&'))}
        data_dict['date'] = datetime.now().isoformat()
        result = collection.insert_one(data_dict)

        logging.info(f"Data successfully saved to MongoDB with ID: {result.inserted_id}. Data: {data_dict}")
    except Exception as e:
        logging.error(f"Error saving data: {e}")



if __name__ == "__main__":
    with ProcessPoolExecutor(max_workers=2) as executor:
        executor.submit(run_http_server)
        executor.submit(run_socket_server)