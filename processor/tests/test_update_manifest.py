import json
from pathlib import Path

p = Path('..') / 'raw_map_data' / 'manifest.json'
manifest = json.loads(p.read_text())
for m in manifest['maps']:
    if m['name'] == 'adak':
        print('Original md5:', m['md5'])
        m['md5'] = 'deadbeefdeadbeefdeadbeefdeadbeef'
        break
p.write_text(json.dumps(manifest, indent=2))
print('Manifest updated')
