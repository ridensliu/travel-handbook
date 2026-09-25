"""Add navigation to known place names, preserving itinerary text and source links.
Run on the current page; idempotent. Do not run the legacy itinerary generator.
"""
import html
import json
import re
from pathlib import Path
from urllib.parse import quote
ROOT = Path(__file__).resolve().parents[1]

def link_places(page, places):
    pattern = re.compile('|'.join(re.escape(p) for p in sorted(places, key=len, reverse=True)), re.I)
    lookup = {name.lower(): destination for name, destination in places.items()}
    # Preserve markup verbatim. Only text outside scripts, styles, head and existing links changes.
    skip = []
    result = []
    for token in re.split(r'(<[^>]+>)', page):
        if token.startswith('<'):
            match = re.match(r'<(/?)([\w-]+)', token)
            if match:
                closing, tag = match.groups(); tag = tag.lower()
                if tag in ('head', 'script', 'style', 'a'):
                    if closing:
                        if skip and skip[-1] == tag: skip.pop()
                    else: skip.append(tag)
            result.append(token)
        elif skip:
            result.append(token)
        else:
            def replace(match):
                name = match.group()
                # Avoid matching airport codes inside unrelated words.
                if name.isascii() and len(name) <= 3:
                    start, end = match.span()
                    if (start and token[start-1].isascii() and token[start-1].isalnum()) or (end<len(token) and token[end].isascii() and token[end].isalnum()):
                        return name
                destination = lookup[name.lower()]
                url = 'https://maps.apple.com/?daddr=' + quote(destination, safe='')
                label = html.escape('导航至' + html.unescape(name), quote=True)
                return f'<a class="place" href="{url}" aria-label="{label}" title="从当前位置导航">{name}</a>'
            result.append(pattern.sub(replace, token))
    return ''.join(result)

if __name__ == '__main__':
    page = ROOT / 'italy-iceland/index.html'
    places = json.loads((ROOT / 'docs/navigation-places.json').read_text())
    page.write_text(link_places(page.read_text(), places))
