"""Versioned, domain-separated Ed25519 messages; no command strings or credentials."""
import hashlib,json,re,secrets,time
from urllib.parse import urlsplit
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey,Ed25519PublicKey

VERSION=1
MAX_MESSAGE=240000
MAX_ARCHIVE=64*1024*1024
CHUNK_SIZE=128*1024

class ProtocolError(ValueError):pass

def require(condition,code):
    if not condition:raise ProtocolError(code)

def fields(value,names):
    require(type(value) is dict and set(value)==set(names.split()),'message_fields_invalid')

def hex_value(value,size=64):
    require(type(value) is str and re.fullmatch('[0-9a-f]{'+str(size)+'}',value) is not None,'message_hex_invalid')
    return value

def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')

def parse(raw):
    require(type(raw) is bytes and len(raw)<=MAX_MESSAGE,'message_size_invalid')
    def pairs(items):
        result={}
        for key,value in items:
            require(key not in result,'message_duplicate_field');result[key]=value
        return result
    try:return json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda _:require(False,'message_number_invalid'))
    except (UnicodeError,ValueError,RecursionError):raise ProtocolError('message_json_invalid') from None

def origin(value):
    require(type(value) is str and len(value)<=200,'origin_invalid')
    parsed=urlsplit(value)
    require(parsed.scheme=='https' and parsed.hostname and parsed.path=='' and not parsed.query and
        not parsed.fragment and not parsed.username and not parsed.password and value=='https://'+parsed.netloc,'origin_invalid')
    return value

def private(seed):
    return Ed25519PrivateKey.from_private_bytes(bytes.fromhex(hex_value(seed)))

def public(seed):return private(seed).public_key().public_bytes_raw().hex()

def sign(seed,kind,payload):
    require(kind in {'enrollment','request','response'},'message_kind_invalid')
    return {'payload':payload,'signature':private(seed).sign(b'resmgrcheck.runner.v1.'+kind.encode()+b'\n'+canonical(payload)).hex()}

def verify(key,kind,message):
    fields(message,'payload signature');hex_value(key);hex_value(message['signature'],128)
    try:Ed25519PublicKey.from_public_bytes(bytes.fromhex(key)).verify(bytes.fromhex(message['signature']),b'resmgrcheck.runner.v1.'+kind.encode()+b'\n'+canonical(message['payload']))
    except (InvalidSignature,ValueError):raise ProtocolError('message_authentication_failed') from None
    return message['payload']

def request(seed,runner_id,audience,body):
    return sign(seed,'request',{'version':VERSION,'runner_id':runner_id,'audience':origin(audience),
        'timestamp':int(time.time()),'nonce':secrets.token_hex(16),'body':body})

def fresh(payload,audience):
    require(payload['version']==VERSION and type(payload['version']) is int,'protocol_incompatible')
    require(payload['audience']==origin(audience),'message_audience_mismatch')
    require(type(payload['timestamp']) is int and abs(time.time()-payload['timestamp'])<=60,'message_expired')
    hex_value(payload['nonce'],32)

def fingerprint(value):return hashlib.sha256(canonical(value)).hexdigest()
