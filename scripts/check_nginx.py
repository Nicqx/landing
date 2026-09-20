#!/usr/bin/env python3
"""CI smoke test using the actual pinned image and production security settings."""
import json
from pathlib import Path
import subprocess
import time
import urllib.error
import urllib.request

root = Path(__file__).resolve().parents[1]
resources = json.loads((root / 'k8s/resources.json').read_text())
image = next(x for x in resources if x['kind'] == 'Deployment')['spec']['template']['spec']['containers'][0]['image']
command = ['docker', 'run', '-d', '--rm', '--read-only', '--user', '1000:1000',
           '--cap-drop=ALL', '--security-opt=no-new-privileges', '--tmpfs', '/tmp:rw,uid=1000,gid=1000,size=33554432',
           '-p', '127.0.0.1:18080:8080',
           '-v', str(root / 'site') + ':/usr/share/nginx/html:ro',
           '-v', str(root / 'nginx.conf') + ':/etc/nginx/nginx.conf:ro',
           '--entrypoint', 'nginx', image, '-g', 'daemon off;']
container = subprocess.check_output(command, text=True).strip()
try:
    for attempt in range(30):
        try:
            with urllib.request.urlopen('http://127.0.0.1:18080/healthz', timeout=2) as response:
                assert response.read() == b'ok\n'
            break
        except (OSError, urllib.error.URLError):
            time.sleep(1)
    else:
        subprocess.run(['docker', 'logs', container], check=False)
        raise RuntimeError('nginx did not become healthy with the production security settings')
    for path in ['/', '/style.css', '/app.js']:
        with urllib.request.urlopen('http://127.0.0.1:18080' + path, timeout=5) as response:
            assert response.status == 200
            assert "script-src 'self'" in response.headers['Content-Security-Policy']
            assert response.headers['X-Content-Type-Options'] == 'nosniff'
    print('Pinned nginx image: health, assets and security headers passed.')
finally:
    subprocess.run(['docker', 'stop', container], check=True, stdout=subprocess.DEVNULL)
