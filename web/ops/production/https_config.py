"""Exact-host nginx1.24 config; no catch-all, TCP backend or secret-bearing logging."""
import re
HOST='qnx-resmgrcheck.gestionatech.de'
CSP="default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; frame-src 'self'; frame-ancestors 'none'; object-src 'none'; base-uri 'none'; form-action 'self'"

def http_config():
    return '''# ResMgrCheck only. No URI, query, body, cookie, authorization or raw IP in access logs.
log_format resmgrcheck_safe '$request_id $request_method $resmgrcheck_area $status $request_time';
map $uri $resmgrcheck_area {
    default public;
    ~^/administrator/ administrator;
    ~^/access/ access;
    ~^/app/ application;
    ~^/api/ api;
    ~^/runner/ runner-disabled;
    ~^/demo/ playback;
}
# Retain the installed zone's key/size so a graceful reload can reuse it safely.
limit_req_zone $binary_remote_addr zone=resmgrcheck_auth:10m rate=10r/m;
map "$request_method:$uri" $resmgrcheck_auth_post_key {
    default "";
    ~^POST:/(administrator/|access/) $realip_remote_addr;
}
limit_req_zone $resmgrcheck_auth_post_key zone=resmgrcheck_auth_post:1m rate=10r/m;
map $upstream_http_content_security_policy $resmgrcheck_csp {
    default $upstream_http_content_security_policy;
    "" "'''+CSP+'''";
}
map $upstream_http_x_frame_options $resmgrcheck_frame {
    default DENY;
    SAMEORIGIN SAMEORIGIN;
}
'''

def headers(indent='    ',cache=True):
    pairs=[('Strict-Transport-Security','max-age=31536000'),('X-Content-Type-Options','nosniff'),
        ('X-Frame-Options','$resmgrcheck_frame'),('Referrer-Policy','same-origin'),
        ('Permissions-Policy','camera=(), microphone=(), geolocation=()'),('Content-Security-Policy','$resmgrcheck_csp')]
    if cache:pairs.append(('Cache-Control','no-store'))
    return ''.join(indent+'add_header '+name+' "'+value+'" always;\n' for name,value in pairs)

def site_config(revision):
    if not re.fullmatch('[0-9a-f]{40}',revision):raise ValueError('Exact immutable application release required')
    return '''# ResMgrCheck HTTPS only; generated from a reviewed immutable driver.
server {
    listen 80;
    listen [::]:80;
    server_name '''+HOST+''';
    access_log /var/log/nginx/resmgrcheck-access.log resmgrcheck_safe;
    error_log /var/log/nginx/resmgrcheck-error.log crit;
    server_tokens off;
    location ^~ /.well-known/acme-challenge/ {
        root /var/www/resmgrcheck-acme;
        default_type text/plain;
        limit_except GET { deny all; }
        try_files $uri =404;
    }
    location / { return 308 https://'''+HOST+'''$request_uri; }
}
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name '''+HOST+''';
    ssl_certificate /etc/letsencrypt/live/'''+HOST+'''/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/'''+HOST+'''/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_session_cache shared:resmgrcheck_tls:1m;
    ssl_session_tickets off;
    server_tokens off;
    client_max_body_size 256k;
    client_body_timeout 10s;
    client_header_timeout 10s;
    send_timeout 30s;
    access_log /var/log/nginx/resmgrcheck-access.log resmgrcheck_safe;
    error_log /var/log/nginx/resmgrcheck-error.log crit;
    limit_req zone=resmgrcheck_auth_post burst=8 nodelay;
    limit_req_status 429;
'''+headers()+'''    location /static/ {
        alias /var/lib/resmgrcheck/static/'''+revision+'''/;
        autoindex off;
'''+headers('        ',False)+'''        add_header Cache-Control "public, max-age=300" always;
    }
    location ~ (^|/)\\. { return 404; }
    # Deployment contract: customer-host qualification is still outstanding.
    location ^~ /runner/ { return 404; }
    location / {
        proxy_pass http://unix:/run/resmgrcheck-web/application.sock;
        proxy_set_header Host '''+HOST+''';
        proxy_set_header X-Real-IP $realip_remote_addr;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header X-Forwarded-For '';
        proxy_set_header Forwarded '';
        proxy_cache off;
        proxy_buffering off;
        gzip off;
        proxy_hide_header Strict-Transport-Security;
        proxy_hide_header X-Content-Type-Options;
        proxy_hide_header X-Frame-Options;
        proxy_hide_header Referrer-Policy;
        proxy_hide_header Permissions-Policy;
        proxy_hide_header Content-Security-Policy;
        proxy_hide_header Cache-Control;
        proxy_connect_timeout 5s;
        proxy_read_timeout 35s;
        proxy_send_timeout 35s;
    }
}
'''

def renewal_hook():
    # Directory hooks run for every lineage. Exact match makes other renewals no-ops.
    return '''#!/bin/sh
set -eu
[ "${RENEWED_LINEAGE:-}" = "/etc/letsencrypt/live/'''+HOST+'''" ] || exit 0
[ "${RENEWED_DOMAINS:-}" = "'''+HOST+'''" ] || exit 0
/usr/sbin/nginx -t -q
/usr/bin/systemctl reload nginx.service
'''
