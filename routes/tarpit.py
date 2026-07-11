import os
import random
import string
import json
from flask import Blueprint, send_file, Response, request, redirect

tarpit_bp = Blueprint('tarpit', __name__)

# common scanner endpoints
SENSITIVE_FILES = [
    '/.env', '/.env.local', '/.env.production', '/.env.development',
    '/docker-compose.yml', '/docker-compose.yaml', '/Dockerfile',
    '/.aws/credentials', '/.aws/config', '/config.json',
    '/secrets.yml', '/config.yml', '/database.yml',
    '/.gitignore', '/.svn/entries'
]

GIT_FILES = ['/.git/config', '/.git/HEAD', '/.git/logs/HEAD']

BACKUP_FILES = [
    '/database.tar.bz2', '/1.gz', '/dump.tgz', '/backup.zip', '/backup.tar.gz',
    '/db.sql', '/dump.sql', '/database.sqlite', '/db.sqlite3',
    '/wwwroot.zip', '/site.zip', '/html.zip', '/var/www/html.zip',
    '/source.zip', '/src.zip', '/backup.sql'
]

WP_FILES = [
    '/wp-admin', '/wp-login.php', '/wp-config.php', '/wp-content/debug.log',
    '/xmlrpc.php', '/wp-includes', '/wp-content/uploads'
]

API_FILES = [
    '/api/v1/users', '/swagger.json', '/openapi.json', '/api-docs',
    '/swagger-ui.html', '/graphql', '/graphiql'
]

SPIDER_TRAP_DIRS = [
    '/old', '/dev', '/test', '/staging', '/bak', '/backup',
    '/administrator', '/admin', '/phpmyadmin', '/pma', '/dashboard'
]

SQL_FILES = [
    '/user.php', '/item.php', '/product.php', '/article.php', '/news.php',
    '/category.php', '/search.php', '/index.php'
]

OTHER_FILES = [
    '/phpinfo.php', '/info.php', '/server-status', '/actuator', '/actuator/env',
    '/.idea/workspace.xml'
]

KUBE_FILES = ['/.kube/config', '/var/run/docker.sock']
PROMETHEUS_FILES = ['/metrics', '/api/datasources']
NODE_FILES = ['/package.json', '/package-lock.json']
SSH_FILES = ['/.ssh/id_rsa', '/.ssh/id_ed25519', '/.ssh/known_hosts', '/id_rsa', '/id_rsa.pub', '/known_hosts']
LOG_FILES = ['/var/log/syslog', '/app.log', '/debug.log', '/laravel.log', '/.pm2/logs', '/error.log']

ALL_ROUTES = SENSITIVE_FILES + GIT_FILES + BACKUP_FILES + WP_FILES + API_FILES + SPIDER_TRAP_DIRS + SQL_FILES + OTHER_FILES + KUBE_FILES + PROMETHEUS_FILES + NODE_FILES + SSH_FILES + LOG_FILES

def generate_fake_aws_key():
    return "AKIA" + "".join(random.choices(string.ascii_uppercase + string.digits, k=16))

def generate_fake_aws_secret():
    return "".join(random.choices(string.ascii_letters + string.digits + "/", k=40))

def generate_fake_env():
    lines = []
    # interesting fake credentials
    for _ in range(50): 
        lines.append(f"AWS_ACCESS_KEY_ID={generate_fake_aws_key()}")
        lines.append(f"AWS_SECRET_ACCESS_KEY={generate_fake_aws_secret()}")
        lines.append(f"DB_PASSWORD={''.join(random.choices(string.ascii_letters + string.digits, k=16))}")
        lines.append(f"STRIPE_API_KEY=sk_live_{''.join(random.choices(string.ascii_letters + string.digits, k=24))}")
        lines.append(f"JWT_SECRET={''.join(random.choices(string.ascii_letters + string.digits, k=32))}")
        lines.append(f"SLACK_BOT_TOKEN=xoxb-{''.join(random.choices(string.digits, k=11))}-{''.join(random.choices(string.digits, k=11))}-{''.join(random.choices(string.ascii_letters + string.digits, k=24))}")
        lines.append("")
    return "\n".join(lines)

def generate_fake_git_config():
    return """[core]
\trepositoryformatversion = 0
\tfilemode = true
\tbare = false
\tlogallrefupdates = true
[remote "origin"]
\turl = git@github.com:quantumlogic/quantum-core-repo.git
\tfetch = +refs/heads/*:refs/remotes/origin/*
"""

def generate_fake_kubeconfig():
    return """apiVersion: v1
clusters:
- cluster:
    certificate-authority-data: LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCg==
    server: https://10.0.0.1:6443
  name: production-k8s
contexts:
- context:
    cluster: production-k8s
    user: admin
  name: default
current-context: default
kind: Config
preferences: {}
users:
- name: admin
  user:
    client-certificate-data: LS0tLS1CRUdJTiBDRVJUSUZJQ0FURS0tLS0tCg==
    client-key-data: LS0tLS1CRUdJTiBSU0EgUFJJVkFURSBLRVktLS0tLQo=
"""

def generate_fake_metrics():
    lines = ["# HELP node_cpu_seconds_total Seconds the CPUs spent in each mode.", "# TYPE node_cpu_seconds_total counter"]
    for i in range(16):
        lines.append(f'node_cpu_seconds_total{{cpu="{i}",mode="idle"}} {random.uniform(1000, 9000):.2f}')
        lines.append(f'node_cpu_seconds_total{{cpu="{i}",mode="system"}} {random.uniform(10, 900):.2f}')
    return "\\n".join(lines) + "\\n"

def generate_fake_package_json():
    return json.dumps({
        "name": f"project-{''.join(random.choices(string.ascii_lowercase, k=8))}",
        "version": "1.0.0",
        "dependencies": {
            "express": "^4.17.1",
            "lodash": "^4.17.21",
            "mongoose": "^5.11.15",
            "pad-left": "^2.1.0",
            "is-ten-thousand": "^2.0.0",
            "true": "^0.0.4",
            "is-even-ai": "^1.0.5"
        }
    })

def generate_fake_ssh_key():
    key_body = ""
    for _ in range(37):
        key_body += "".join(random.choices(string.ascii_letters + string.digits + "+/", k=64)) + "\n"
    key_body += "".join(random.choices(string.ascii_letters + string.digits + "+/", k=24)) + "=="
    return f"-----BEGIN RSA PRIVATE KEY-----\n{key_body}\n-----END RSA PRIVATE KEY-----\n"

def generate_fake_logs():
    levels = ["INFO", "WARNING", "ERROR", "CRITICAL", "DEBUG"]
    ips = [f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}" for _ in range(10)]
    messages = [
        "Connection refused from {ip}",
        "Failed password for invalid user admin from {ip} port {port} ssh2",
        "Exception in thread 'main' java.lang.NullPointerException at com.app.auth.LoginValidator.validate(LoginValidator.java:42)",
        "User 'admin' logged in successfully from {ip}",
        "Database connection timeout. Retrying in 5 seconds...",
        "AWS credentials successfully loaded from ~/.aws/credentials",
        "API rate limit exceeded for {ip}",
        "Invalid JWT token received: signature verification failed",
        "SQL Syntax Error near '1' or 1=1' at line 1"
    ]
    lines = []
    for _ in range(1000):
        level = random.choice(levels)
        ip = random.choice(ips)
        port = random.randint(1024, 65535)
        msg = random.choice(messages).format(ip=ip, port=port)
        timestamp = f"2026-{random.randint(1,12):02d}-{random.randint(1,28):02d}T{random.randint(0,23):02d}:{random.randint(0,59):02d}:{random.randint(0,59):02d}Z"
        lines.append(f"[{timestamp}] [{level}] {msg}")
    return "\n".join(lines)

def generate_fake_json():
    # fake users to mess with JSON parsers
    users = []
    for i in range(500):
        users.append({
            "id": i,
            "username": f"admin_{''.join(random.choices(string.ascii_letters, k=5))}",
            "email": f"admin{i}@internal.corp",
            "password_hash": f"$2b$12${''.join(random.choices(string.ascii_letters + string.digits + './', k=53))}",
            "role": "SUPER_ADMIN"
        })
    return json.dumps(users)

def generate_spider_trap(path):
    from markupsafe import escape
    # generates a fake directory listing with hundreds of random links to trap crawlers
    links = []
    for _ in range(200):
        fake_dir = ''.join(random.choices(string.ascii_lowercase, k=8))
        fake_file = ''.join(random.choices(string.ascii_lowercase, k=8)) + random.choice(['.php', '.html', '.bak', '.txt', '/'])
        # link back to a trap directory 
        base_dir = random.choice(SPIDER_TRAP_DIRS)
        links.append(f'<tr><td><a href="{base_dir}/{fake_dir}/{fake_file}">{fake_file}</a></td><td>{random.randint(10, 5000)}K</td></tr>')
    
    safe_path = escape(path)
    html = f"""
    <html><head><title>Index of {safe_path}</title></head>
    <body bgcolor="white">
    <h1>Index of {safe_path}</h1><hr><table width="100%" border="0">
    <tr><th>Name</th><th>Size</th></tr>
    {''.join(links)}
    </table><hr>
    </body></html>
    """
    return html

def generate_fake_sql_error():
    # looks like a possible SQL injection
    errors = [
        "You have an error in your SQL syntax; check the manual that corresponds to your MySQL server version for the right syntax to use near '' at line 1",
        "Warning: pg_query(): Query failed: ERROR: syntax error at or near \"'\" in /var/www/html/db.php on line 42",
        "System.Data.SqlClient.SqlException (0x80131904): Unclosed quotation mark after the character string ''."
    ]
    html = f"<br /><b>Fatal error</b>: Uncaught exception 'PDOException' with message '{random.choice(errors)}' in /var/www/html/database.php:82<br />Stack trace:<br />#0 /var/www/html/index.php(12): PDO->query()<br />#1 {{main}}<br />  thrown in <b>/var/www/html/database.php</b> on line <b>82</b><br />"
    return Response(html, status=500, mimetype='text/html')

def setup_tarpit(bp):
    @bp.route('/robots.txt', methods=['GET', 'POST', 'HEAD', 'OPTIONS'])
    def robots_txt():
        lines = ["User-agent: *"]
        # bait scanners into hitting our tarpit routes by listing them all here
        # while also stopping legitimate scanners from getting baited
        for route in sorted(set(ALL_ROUTES)):
            lines.append(f"Disallow: {route}")
        return Response("\n".join(lines), mimetype='text/plain')

    def handle_tarpit(*args, **kwargs):
        path = request.path
        
        if any(path.startswith(p) for p in WP_FILES):
            # endless redirect loop between WP files to break crawlers that follow redirects
            next_path = random.choice([p for p in WP_FILES if p != path])
            status_code = random.choice([301, 302, 307, 308])
            response = redirect(next_path, code=status_code)
            # add some fake cookies to mess with a cookie jar, if they use one
            for i in range(10):
                response.set_cookie(f'wp_sess_{i}', ''.join(random.choices(string.ascii_letters, k=64)))
            return response
            
        elif any(path.startswith(p) for p in GIT_FILES):
            return Response(generate_fake_git_config(), mimetype='text/plain')
            
        elif any(path.startswith(p) for p in SENSITIVE_FILES):
            return Response(generate_fake_env(), mimetype='text/plain')
            
        elif any(path.startswith(p) for p in API_FILES):
            return Response(generate_fake_json(), mimetype='application/json')
            
        elif any(path.startswith(p) for p in KUBE_FILES):
            return Response(generate_fake_kubeconfig(), mimetype='application/x-yaml')
            
        elif any(path.startswith(p) for p in PROMETHEUS_FILES):
            return Response(generate_fake_metrics(), mimetype='text/plain')
            
        elif any(path.startswith(p) for p in NODE_FILES):
            return Response(generate_fake_package_json(), mimetype='application/json')
            
        elif any(path.startswith(p) for p in SSH_FILES):
            return Response(generate_fake_ssh_key(), mimetype='text/plain')
            
        elif any(path.startswith(p) for p in LOG_FILES):
            return Response(generate_fake_logs(), mimetype='text/plain')
            
        elif any(path.startswith(p) for p in SPIDER_TRAP_DIRS):
            return Response(generate_spider_trap(path), mimetype='text/html')
            
        elif any(path.startswith(p) for p in SQL_FILES) or any(k in request.args for k in ['id', 'page', 'user', 'query']):
            return generate_fake_sql_error()
            
        elif any(path.startswith(p) for p in BACKUP_FILES) or 'gzip' in request.headers.get('Accept-Encoding', '').lower():
            # gzip bomb for backup files
            bomb_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'bomb-do-not-extract.gz')
            
            # if they hit a backup file but support gzip, just send it as binary attachment
            if path.endswith('.zip') or path.endswith('.sql'):
                return send_file(bomb_path, as_attachment=True, download_name='backup' + os.path.splitext(path)[1])
                
            response = send_file(bomb_path, mimetype='text/html')
            response.headers['Content-Encoding'] = 'gzip'
            return response
            
        else:
            response = Response("Unauthorized access. This incident has been reported.", 401)
            response.headers['WWW-Authenticate'] = 'Basic realm="Restricted Area"'
            return response

    for route in ALL_ROUTES:
        bp.route(route, methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS'])(handle_tarpit)
        bp.route(f"{route}/<path:subpath>", methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS'])(handle_tarpit)

setup_tarpit(tarpit_bp)
