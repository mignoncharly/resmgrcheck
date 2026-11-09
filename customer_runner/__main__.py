"""Operator CLI. Enrollment secret is file-only; no keys/tokens in argv or stdout."""
import argparse,fcntl,json,os,secrets,stat,time
from pathlib import Path
from . import protocol as wire
from .client import Client,create,protected
from .agent import config,discover,route_fingerprint

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('operation',choices=['enroll','heartbeat'])
    p.add_argument('--config',required=True);p.add_argument('--state',required=True);p.add_argument('--enrollment-file')
    p.add_argument('--ca-file',help='Optional explicit trusted CA bundle; TLS verification is always enabled')
    args=p.parse_args();os.umask(0o077)
    try:
        configuration=config(args.config);state=Path(args.state)
        wire.require(state.is_absolute() and not any(x.is_symlink() for x in [state,*state.parents]),'state_path_invalid')
        state.mkdir(mode=0o700,parents=True,exist_ok=True);info=state.lstat()
        wire.require(info.st_uid==os.geteuid() and stat.S_IMODE(info.st_mode)==0o700,'state_ownership_invalid')
        fd=os.open(state/'runner.lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
        try:
            info=os.fstat(fd);wire.require(stat.S_ISREG(info.st_mode) and info.st_uid==os.geteuid() and info.st_nlink==1 and stat.S_IMODE(info.st_mode)==0o600,'runner_lock_invalid')
            fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            key=state/'device-key'
            if not key.exists():create(key,secrets.token_hex(32).encode())
            seed=protected(key,64).decode('ascii');wire.hex_value(seed)
            binding={name:configuration[name] for name in ['origin','server_public_key','target_id','organization_id','project_id']}
            binding['route_sha256']=route_fingerprint(configuration)
            record=state/'binding.json'
            if not record.exists():create(record,wire.canonical(binding))
            wire.require(wire.parse(protected(record))==binding,'local_target_switch_refused')
            discovery=state/('discovery-'+secrets.token_hex(8)+'.json');inventory=discover(configuration,discovery)
            client=Client(configuration['origin'],configuration['server_public_key'],seed,configuration['target_id'],ca_file=args.ca_file)
            if args.operation=='enroll':
                wire.require(bool(args.enrollment_file),'enrollment_file_required')
                token=protected(Path(args.enrollment_file),128).decode('ascii').strip()
                result=client.enroll(token,inventory)
                wire.require(result['organization_id']==configuration['organization_id'] and result['project_id']==configuration['project_id'],'enrollment_tenant_mismatch')
            else:result=client.exchange({'operation':'heartbeat','inventory':inventory})
            print(json.dumps({'state':result['state'],'runner_public_key':wire.public(seed),'inventory_sha256':wire.fingerprint(inventory),'native_test_executed':False}))
        finally:os.close(fd)
    except (wire.ProtocolError,OSError,ValueError,KeyError,TypeError):
        # Never reflect config, remote bodies, exceptions or credentials.
        raise SystemExit('Customer runner action failed safely; inspect local configuration and non-secret status.') from None

if __name__=='__main__':main()
