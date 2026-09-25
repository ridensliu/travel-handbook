import re, unittest
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlparse, parse_qs

PAGE = Path(__file__).resolve().parents[1] / 'italy-iceland/index.html'
class Links(HTMLParser):
    def __init__(self, html):
        super().__init__(); self.links=[]; self.current=None; self.feed(html)
    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            assert self.current is None, 'Nested links'
            self.current=[dict(attrs), '']
    def handle_data(self, text):
        if self.current is not None: self.current[1]+=text
    def handle_endtag(self, tag):
        if tag == 'a' and self.current is not None:
            self.links.append(self.current); self.current=None
class NavigationTest(unittest.TestCase):
    def test_named_places_and_separate_stops(self):
        links=Links(PAGE.read_text()).links
        for name in ['trattoria za za','圣洛伦佐教堂','圣母百花教堂','共和国广场','老桥','Hotel Tyrol','Jökulsárlón','KEF','LHR T5','the fish company']:
            found=[a for a,t in links if t==name and 'place' in a.get('class','')]
            self.assertTrue(found, name+' must be navigable')
            for a in found:
                u=urlparse(a['href']); self.assertEqual(u.netloc,'www.google.com')
                self.assertEqual(u.path,'/maps/dir/')
                query=parse_qs(u.query)
                self.assertEqual(query.get('api'),['1'])
                self.assertTrue(query.get('destination'))
                self.assertEqual(query.get('dir_action'),['navigate'])
                self.assertNotIn('target',a)
    def test_no_placeholder_navigation(self):
        for a,t in Links(PAGE.read_text()).links:
            if 'place' in a.get('class',''):
                self.assertNotIn(t,['酒店','指定接客点','活动基地','休息'])
    def test_original_reference_links_remain(self):
        self.assertIn('https://sanlorenzofirenze.it/info-visite/', PAGE.read_text())
if __name__=='__main__': unittest.main()
