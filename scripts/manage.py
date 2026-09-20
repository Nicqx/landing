#!/usr/bin/env python3
import json
from common import restore_snapshot
from common import (ROOT, Kube, checksum, diagnose, entrypoint, label, operation_lock,
                    parser, rollout, snapshot)

ALLOWED = {('ConfigMap', 'landing-page'), ('ConfigMap', 'landing-nginx'),
           ('Deployment', 'landing-page-deployment'), ('Service', 'landing-page-service')}


def render(kube=None):
    items = json.loads((ROOT / 'k8s/resources.json').read_text())
    assets, nginx, deployment, service = items
    assets['data'] = {name: (ROOT / 'site' / name).read_text() for name in ['index.html', 'style.css', 'app.js']}
    nginx['data'] = {'nginx.conf': (ROOT / 'nginx.conf').read_text()}
    deployment['spec']['template']['metadata']['annotations'] = {
        'nicqx.dev/config-sha256': checksum([assets['data'], nginx['data']])}
    if kube:
        old = kube.get('deployment', 'landing-page-deployment')
        if old: deployment['spec']['replicas'] = old['spec'].get('replicas', 1)
    return label(items, 'landing')


def main():
    p = parser('Jatekkezdo frissitese', ['update', 'rollback', 'render', 'diagnose'])
    p.add_argument('--file')
    args = p.parse_args()
    if args.command == 'render':
        print(json.dumps(render(), indent=2)); return
    if args.dry_run and args.command not in {'update', 'rollback'}: p.error('--dry-run csak update mellett ervenyes')
    kube = Kube(args.target, args.context)
    kube.verify(require_ready=args.command != 'diagnose')
    if args.command == 'diagnose': diagnose(kube); return
    with operation_lock(args.target):
        if args.command == 'rollback':
            if not args.file: p.error('--file szukseges')
            restore_snapshot(kube, args.file, ALLOWED, args.dry_run)
            return
        items = render(kube)
        if not args.dry_run: snapshot(kube, items)
        kube.apply(items, ALLOWED, dry_run=args.dry_run)
        if not args.dry_run: rollout(kube, items)


if __name__ == '__main__':
    entrypoint(main)
