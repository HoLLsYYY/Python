"""Authenticated, short-lived commands. Relay sees only ciphertext."""
import base64, hashlib, json, secrets, time
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

COMMANDS={'heart','shy','bouquet','show','hide','ack'}
def new_code():
    return 'BEAR1-'+secrets.token_urlsafe(32)
def key_for(code):
    if not code.startswith('BEAR1-'):
        raise ValueError('Нужен код BEAR1-… с компьютера мишки')
    raw=base64.urlsafe_b64decode(code[6:]+'='*(-len(code[6:])%4))
    if len(raw)!=32: raise ValueError('Неполный код сопряжения')
    return raw
def topic_for(code):
    return 'bear-'+hashlib.sha256(key_for(code)+b'topic-v1').hexdigest()[:56]
def encode(code,command,ref=None,sender=None,target=None,reply_to=None):
    if command not in COMMANDS: raise ValueError('Unknown command')
    data={'cmd':command,'id':secrets.token_hex(16),'time':time.time()}
    if ref: data['ref']=ref
    if sender:data['sender']=sender
    if target:data['target']=target
    if reply_to:data['reply_to']=reply_to
    nonce=secrets.token_bytes(12)
    blob=nonce+AESGCM(key_for(code)).encrypt(nonce,json.dumps(data).encode(),b'bear-v1')
    return base64.urlsafe_b64encode(blob).decode(),data['id']
def decode(code,payload,seen,now=None):
    blob=base64.urlsafe_b64decode(payload)
    data=json.loads(AESGCM(key_for(code)).decrypt(blob[:12],blob[12:],b'bear-v1'))
    now=time.time() if now is None else now
    if data.get('cmd') not in COMMANDS or not isinstance(data.get('id'),str): raise ValueError('Invalid command')
    if not -15<=now-data['time']<=60: raise ValueError('Expired command')
    if data['id'] in seen: raise ValueError('Replay')
    seen.add(data['id'])
    return data

