#!/usr/bin/env bash
set -euo pipefail

[[ ${EUID} -eq 0 ]] || { echo 'Run with sudo.' >&2; exit 1; }
[[ -f /opt/jjm-rag/current/deployment/rhel7/templates/jjm-rag-httpd.conf ]] || { echo 'Install the application first.' >&2; exit 1; }
httpd -M | grep -q 'proxy_module' || { echo 'Apache proxy_module is not enabled.' >&2; exit 1; }
httpd -M | grep -q 'proxy_http_module' || { echo 'Apache proxy_http_module is not enabled.' >&2; exit 1; }
httpd -M | grep -q 'headers_module' || { echo 'Apache headers_module is not enabled.' >&2; exit 1; }
httpd -M | grep -q 'ssl_module' || { echo 'Apache ssl_module is not enabled.' >&2; exit 1; }
install -m 0640 /opt/jjm-rag/current/deployment/rhel7/templates/jjm-rag-httpd.conf /etc/httpd/conf.d/jjm-rag.conf
echo 'Edit /etc/httpd/conf.d/jjm-rag.conf: replace every REPLACE_WITH value, then run sudo httpd -t.'
