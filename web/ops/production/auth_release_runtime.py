#!/usr/bin/env python3
"""Root-only new-release assets/schema check; no migrations or account changes."""
import argparse,json,sys
from pathlib import Path
sys.dont_write_bytecode=True # -I ignores PYTHONDONTWRITEBYTECODE; protect immutable source.
sys.path.insert(0,str(Path(__file__).resolve().parent))
import acceptance_operator as acceptance
from https_checks import require

def main(revision):
    acceptance.load_application(revision)
    from django.conf import settings
    from django.db import connection
    from django.db.migrations.executor import MigrationExecutor
    from django.test import RequestFactory
    from allauth.account.adapter import get_adapter
    from control.management.commands.private_release import assets
    require(settings.ALLAUTH_TRUSTED_CLIENT_IP_HEADER=='X-Real-IP','trusted_proxy_identity_not_configured')
    executor=MigrationExecutor(connection)
    require(not executor.migration_plan(executor.loader.graph.leaf_nodes()),'unexpected_database_migrations')
    request=RequestFactory().post('/',REMOTE_ADDR='',HTTP_X_REAL_IP='198.51.100.20',HTTP_X_FORWARDED_FOR='192.0.2.2')
    require(get_adapter().get_client_ip(request)=='198.51.100.20','trusted_proxy_identity_check_failed')
    assets(revision)
    print(json.dumps({'passed':True,'revision':revision,'authentication_policy':'administrator-password-only-v1','administrator_MFA':'deferred',
        'schema_changed':False,'proxy_identity':'validated','new_static_assets':'verified'}))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--release',required=True);args=parser.parse_args()
    try:main(args.release)
    except BaseException:
        print(json.dumps({'passed':False,'failed_check':'auth_release_runtime_check_failed','secrets_printed':False}));raise SystemExit(1) from None
