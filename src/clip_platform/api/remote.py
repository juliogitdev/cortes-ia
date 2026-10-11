"""Entrada remota protegida por autenticação HTTP do navegador."""
import base64
import binascii
import hmac
import json
import os
from pathlib import Path

from clip_platform.api.app import create_app


class BasicAuthGate:
    def __init__(self, app, username: str, password: str):
        if not username or not password:
            raise ValueError('Credenciais remotas obrigatórias.')
        self.app = app
        self.expected = f'{username}:{password}'.encode('utf-8')

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            await self.app(scope, receive, send)
            return
        auth = next((value for name, value in scope['headers'] if name.lower() == b'authorization'), b'')
        valid = False
        if auth.startswith(b'Basic '):
            try:
                supplied = base64.b64decode(auth[6:], validate=True)
                valid = hmac.compare_digest(supplied, self.expected)
            except (ValueError, binascii.Error):
                pass
        if not valid:
            await send({'type': 'http.response.start', 'status': 401,
                        'headers': [(b'www-authenticate', b'Basic realm="Cortes IA", charset="UTF-8"'),
                                    (b'content-type', b'text/plain; charset=utf-8'),
                                    (b'cache-control', b'no-store')]})
            await send({'type': 'http.response.body', 'body': b'Acesso remoto protegido.'})
            return
        await self.app(scope, receive, send)


def create_remote_app():
    auth_file = Path(os.environ['CLIP_REMOTE_AUTH_FILE'])
    credentials = json.loads(auth_file.read_text(encoding='utf-8-sig'))
    return BasicAuthGate(create_app(), credentials['username'], credentials['password'])
