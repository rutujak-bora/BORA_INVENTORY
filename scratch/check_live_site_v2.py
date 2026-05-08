import urllib.request
import re

try:
    html = urllib.request.urlopen('http://13.50.236.19/').read().decode('utf-8')
    js_files = re.findall(r'src="(/static/js/[^"]+)"', html)
    print('JS files in live index.html:', js_files)
    
    found_new_code = False
    for js_file in js_files:
        js_content = urllib.request.urlopen('http://13.50.236.19' + js_file).read().decode('utf-8')
        
        # Look for specific string only added in our new PLReporting.jsx
        if 'placeholder="All Categories"' in js_content or 'filters.company_ids' in js_content or '"categories"' in js_content:
            # We must be careful because StockSummaryNew might have "All Categories".
            # PLReporting uses `from_date: "", to_date: "", company_ids: [], sku: "", categories: []`
            if 'company_ids:[]' in js_content.replace(' ', '') or 'categories:[]' in js_content.replace(' ', ''):
                found_new_code = True
                print(f'Confirmed: Found EXACT NEW PLReporting code in {js_file}')
                break
    
    if not found_new_code:
        print('FAILURE: The live JS bundle does NOT contain the new PLReporting code.')

except Exception as e:
    print('Error:', e)
