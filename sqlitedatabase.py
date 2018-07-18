import os
import random
import string
import logging
from logging.handlers import RotatingFileHandler

import apsw
from flask import Flask, request, jsonify
from werkzeug.exceptions import BadRequest

app = Flask(__name__)


def generate_auth():
    logging.info('Generating new auth config')
    import json
    import shutil
    if not os.path.isfile("config.json"):
        shutil.copy('exampleconfig.json', 'config.json')
    with open('config.json') as read_json:
        data = json.load(read_json)
        AUTH = ''.join([random.choice(string.ascii_letters + string.digits) for _ in range(32)])
        data['DB_AUTH'] = AUTH
        app.__AUTH = AUTH
    with open('config.json', 'w') as write_json:
        json.dump(data, write_json, indent=4)


def verify_auth_header(request):
    if hasattr(app, '__AUTH'):
        return request.headers.get('auth') == app.__AUTH
    return False


@app.route('/test', methods=['GET', 'POST'])
def index():
    if not verify_auth_header(request):
        return jsonify({'response': f'Unauthorized {request.method} request'}), 401
    if request.method == 'GET':
        return jsonify({'response': f'GET request from {request.remote_addr}'})
    if request.method == 'POST':
        mime_type = request.headers.get('content-type')
        if request.is_json:
            try:
                dd = request.get_json()
            except BadRequest:
                return jsonify({'response': 'Failed to parse JSON'}), 400
        else:
            dd = dict(request.form)
        return jsonify({'response': f'POST request from {request.remote_addr}',
                        'data-received': dd,
                        'type': mime_type})


@app.route('/db/createPrefixesTable')
def db_create_prefixes_table():
    if not verify_auth_header(request):
        return jsonify({'response': 'Unauthorized'}), 401
    cursor = database.cursor()
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS prefixes(
                guild_id BIGINT,
                prefix TEXT,
                unique (guild_id, prefix)
            );
            """)
    except apsw.SQLError as e:
        return jsonify({'response': repr(e)}), 500
    return jsonify({'response': 'Successfully create prefixes table'})


def db_table_exists(table_name: str):
    cursor = database.cursor()
    return list(cursor.execute("""SELECT 1 FROM sqlite_master WHERE type='table' AND name=?;""", (table_name,)))


@app.route('/db/getPrefixes/<int:guild_id>')
def db_get_prefixes(guild_id: int):
    if not verify_auth_header(request):
        return jsonify({'response': 'Unauthorized'}), 401
    if db_table_exists('prefixes'):
        cursor = database.cursor()
        result = cursor.execute("""SELECT prefix FROM prefixes WHERE guild_id = ?;""", (guild_id,))
        prefixes = [i[0] for i in result]
        return jsonify({'response': f'Prefixes for {guild_id}',
                        'result': prefixes})
    else:
        return jsonify({'response': 'No prefixes table',
                        'result': []})


@app.route('/db/setPrefix', methods=['POST'])
def db_set_prefix():
    if not verify_auth_header(request):
        return jsonify({'response': 'Unauthorized'}), 401
    if request.is_json:
        try:
            dd = request.get_json()
        except BadRequest:
            return jsonify({'response': 'Failed to parse JSON'}), 400
    else:
        dd = dict(request.form)

    if not dd.get('guild_id'):
        return jsonify({'response': 'Missing "guild_id" key'}), 400
    if not dd.get('prefix'):
        return jsonify({'response': 'Missing "prefix" key'}), 400
    try:
        if isinstance(dd.get('guild_id'), list):
            guild_id = int(dd.get('guild_id')[0])
            prefix = str(dd.get('prefix')[0])
        else:
            guild_id = int(dd.get('guild_id'))
            prefix = str(dd.get('prefix'))
    except Exception as e:
        return jsonify({'response': f'Failed to parse: {repr(e)}'}), 400
    else:
        cursor = database.cursor()
        try:
            cursor.execute("""
                INSERT INTO prefixes (guild_id, prefix)
                VALUES (?, ?);
                """, (guild_id, prefix))
        except apsw.ConstraintError:
            return jsonify({'response': f'Prefix already exists'})
        return jsonify({'response': f'Successfully set the prefix {prefix} for {guild_id}'})


@app.route('/db/removePrefix', methods=['DELETE'])
def db_remove_prefix():
    if not verify_auth_header(request):
        return jsonify({'response': 'Unauthorized'}), 401
    if request.is_json:
        try:
            dd = request.get_json()
        except BadRequest:
            return jsonify({'response': 'Failed to parse JSON'}), 400
    else:
        dd = dict(request.form)
    try:
        if isinstance(dd.get('guild_id'), list):
            guild_id = int(dd.get('guild_id')[0])
            prefix = str(dd.get('prefix')[0])
        else:
            guild_id = int(dd.get('guild_id'))
            prefix = str(dd.get('prefix'))
    except Exception as e:
        return jsonify({'response': f'Failed to parse: {repr(e)}'}), 400
    else:
        cursor = database.cursor()
        cursor.execute("""
        DELETE FROM prefixes
        WHERE guild_id=? AND prefix=?
        """, (guild_id, prefix))
        return jsonify({'response': f'Successfully removed the prefix {prefix} from {guild_id}'})


@app.route('/db/countPrefix/<int:guild_id>')
def db_count_prefix(guild_id: int):
    if not verify_auth_header(request):
        return jsonify({'response': 'Unauthorized'}), 401
    cursor = database.cursor()
    result = cursor.execute("""SELECT count(1) FROM prefixes WHERE guild_id = ?;""", (guild_id,))
    count = result[0]
    return jsonify({'response': f'Prefixes for {guild_id}',
                    'result': count})


# region Error handlers

@app.errorhandler(500)
def server_error(err):
    print(err)
    return jsonify({'response': 'Internal server error'}), 500


@app.errorhandler(400)
def bad_request(err):
    print(err)
    return jsonify({'response': 'Unknown bad request'}), 400


@app.errorhandler(404)
def not_found(err):
    print(err)
    return jsonify({'response': f"{request.base_url} doesn't exist"}), 404


@app.errorhandler(405)
def method_not_allowed(err):
    print(err)
    return jsonify({'response': f"{request.method} isn't allowed"}), 405


# endregion

if __name__ == "__main__":
    fh = RotatingFileHandler('logs/sqlite.log', maxBytes=1000000)
    fh.setLevel(logging.DEBUG)
    app.logger.addHandler(fh)

    log = logging.getLogger('werkzeug')
    log.setLevel(logging.DEBUG)
    log.addHandler(fh)

    database = apsw.Connection('alice.db')
    if not hasattr(app, '__AUTH'):
        generate_auth()
    app.run(host='0.0.0.0', port=80, debug=True)
