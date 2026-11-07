"""Private fixed provider child. Credentials cross an anonymous pipe, never argv/logs."""
import json,resource,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from control.ai_provider import Provider,invoke
from control.engine import PolicyError

def main():
    resource.setrlimit(resource.RLIMIT_AS,(256*1024*1024,256*1024*1024))
    resource.setrlimit(resource.RLIMIT_CPU,(25,25));resource.setrlimit(resource.RLIMIT_NOFILE,(64,64))
    try:
        raw=sys.stdin.buffer.read(50001)
        if len(raw)>50000:raise PolicyError('ai_child_input_bound')
        data=json.loads(raw);result=invoke(data['payload'],Provider(**data['provider']))
        sys.stdout.write(json.dumps({'result':result},separators=(',',':')))
    except PolicyError as error:sys.stdout.write(json.dumps({'error':str(error)}))
    except Exception:sys.stdout.write(json.dumps({'error':'ai_child_request_failed'}))
if __name__=='__main__':main()
