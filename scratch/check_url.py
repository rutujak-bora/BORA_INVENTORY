import urllib.request
import re

html = urllib.request.urlopen('http://13.50.236.19/').read().decode('utf-8')
js_files = re.findall(r'src="(/static/js/[^"]+)"', html)
if js_files:
    js_content = urllib.request.urlopen('http://13.50.236.19' + js_files[0]).read().decode('utf-8')
    urls = re.findall(r'"http[s]?://[^"]+"', js_content)
    # Filter for urls ending with api or similar
    api_urls = [u for u in urls if 'api' in u or '13.50' in u or 'bora.tech' in u]
    print('Backend URLs found:', set(api_urls))
