import urllib.request
import re

try:
    html = urllib.request.urlopen('http://13.50.236.19/').read().decode('utf-8')
    js_files = re.findall(r'src="(/static/js/[^"]+)"', html)
    print('JS files:', js_files)
    
    for js_file in js_files:
        js_content = urllib.request.urlopen('http://13.50.236.19' + js_file).read().decode('utf-8')
        if 'MultiSelect' in js_content or 'Category' in js_content:
            print(f'Found MultiSelect/Category in {js_file}')
            break
    else:
        print('Did not find the updated code in the bundles.')
except Exception as e:
    print('Error:', e)
