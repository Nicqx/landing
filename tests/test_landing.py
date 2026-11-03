import json
from html.parser import HTMLParser
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import manage
from common import ROOT


class Page(HTMLParser):
    def __init__(self): super().__init__(); self.tags = []
    def handle_starttag(self, tag, attrs): self.tags.append((tag, dict(attrs)))


class LandingTests(unittest.TestCase):
    def test_all_game_links_stay_on_same_origin(self):
        page = Page(); page.feed((ROOT / 'site/index.html').read_text())
        links = [a['href'] for tag, a in page.tags if tag == 'a']
        self.assertEqual(set(links), {
            '/sumplete/', '/tic-tac-toe/', '/chess/', '/sudoku/',
            '/bakos/', '/maffia/', '/citadella/', '/pandemic/',
            '/pandemic/#lab-preview',
        })
        for _, attrs in page.tags:
            self.assertFalse(any(key.startswith('on') for key in attrs))
        scripts = [a for tag, a in page.tags if tag == 'script']
        self.assertTrue(all('src' in s for s in scripts))

    def test_lab_tile_is_a_link_only_and_never_opens_an_unguarded_port(self):
        page = Page()
        html = (ROOT / 'site/index.html').read_text(encoding='utf-8')
        page.feed(html)
        links = [attrs for tag, attrs in page.tags if tag == 'a']
        lab = [attrs for attrs in links if attrs['href'] == '/pandemic/#lab-preview']
        self.assertEqual(len(lab), 1)
        self.assertFalse(any(attrs.get('target') == '_blank' for attrs in lab))
        self.assertNotIn('127.0.0.1:', html)
        self.assertNotIn('8768', html)
        self.assertNotIn('PANDEMIC_LAB_ENABLE', html)
        self.assertIn('14 szintetikus kártyával', html)
        self.assertIn('meghívós belépéssel', html)

    def test_service_keeps_port_80_with_non_root_backend(self):
        items = manage.render()
        deployment = next(i for i in items if i['kind'] == 'Deployment')
        service = next(i for i in items if i['kind'] == 'Service')
        pod = deployment['spec']['template']['spec']
        self.assertEqual(service['spec']['ports'][0]['port'], 80)
        self.assertEqual(pod['containers'][0]['ports'][0]['containerPort'], 8080)
        self.assertTrue(pod['securityContext']['runAsNonRoot'])
        self.assertTrue(pod['containers'][0]['securityContext']['readOnlyRootFilesystem'])
        self.assertFalse(pod['automountServiceAccountToken'])

    def test_intentionally_stopped_landing_is_not_restarted(self):
        kube = Mock(); kube.get.return_value = {'spec': {'replicas': 0}}
        dep = next(i for i in manage.render(kube) if i['kind'] == 'Deployment')
        self.assertEqual(dep['spec']['replicas'], 0)
