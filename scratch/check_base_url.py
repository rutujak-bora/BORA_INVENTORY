import urllib.request
import re

html = urllib.request.urlopen('http://13.50.236.19/').read().decode('utf-8')
js_files = re.findall(r'src="(/static/js/[^"]+)"', html)
if js_files:
    js_content = urllib.request.urlopen('http://13.50.236.19' + js_files[0]).read().decode('utf-8')
    base_urls = re.findall(r'baseURL:"([^"]+)"', js_content)
    # Also check axios.create({baseURL: "..."}) if it uses single quotes
    base_urls_2 = re.findall(r'baseURL:\'([^\']+)\'', js_content)
    base_urls_3 = re.findall(r'baseURL:([a-zA-Z0-9_\.]+)', js_content)
    print("baseURL (double quotes):", base_urls)
    print("baseURL (single quotes):", base_urls_2)
    print("baseURL (variable):", base_urls_3)
