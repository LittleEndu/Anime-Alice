from flask import Flask, Response, request, jsonify
from werkzeug.routing import Rule

app = Flask(__name__)
app.url_map.add(Rule('/', endpoint='index'))


def verify_auth_header(request):
    return request.headers.get('auth') == "mienai"


@app.route('/')
def index():
    if not verify_auth_header(request):
        return jsonify({'response': f'Unauthorized {request.method} request from {request.path}',
                        'error': 'Unauthorized'}), 401
    if request.method == 'GET':
        return jsonify({'response': f'GET request from {request.path}'})
    if request.method in ['POST', 'PUT']:
        return jsonify({'response': f'{request.method} request from {request.path}',
                        'form-data-recieved': dict(request.form)})
    else:
        return jsonify({'response': f'Unsupported {request.method} request from {request.path}',
                        'error': f'Unsupported method {request.method}'}), 405


@app.errorhandler(500)
def server_error(err):
    return jsonify({'response': 'Internal server error',
                    'error': 'Internal server error'}), 500


if __name__ == "__main__":
    app.run(port=8080)
