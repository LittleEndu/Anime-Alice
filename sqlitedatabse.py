import json
from http.server import BaseHTTPRequestHandler, HTTPServer
import cgi


class SQLiteRequest(BaseHTTPRequestHandler):
    def do_GET(self):
        response = {'response': f"GET request from {self.path}"}

        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(response).encode('utf-8'))

    def do_POST(self):
        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={'REQUEST_METHOD': 'POST'}
        )
        form_dict = {}
        for key in form.keys():
            form_dict[key] = form.getvalue(key)
        response = {'response': f"POST request from {self.path}", 'content': form_dict}

        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(response).encode('utf-8'))


def run(server_class=HTTPServer, handler_class=SQLiteRequest, port=8080):
    server_class(('', port), handler_class).serve_forever()


if __name__ == "__main__":
    from sys import argv

    if len(argv) == 2:
        run(port=int(argv[1]))
    else:
        run()
