import urllib.request
import re

def check_live_config():
    try:
        # Frontend seems to be at 13.50.236.19
        frontend_url = 'http://13.50.236.19/'
        print(f"Fetching frontend from {frontend_url}")
        html = urllib.request.urlopen(frontend_url).read().decode('utf-8')
        
        js_files = re.findall(r'src="(/static/js/[^"]+)"', html)
        print(f"Found JS files: {js_files}")
        
        for js_file in js_files:
            js_url = f"http://13.50.236.19{js_file}"
            print(f"Checking {js_url}")
            js_content = urllib.request.urlopen(js_url).read().decode('utf-8')
            
            # Look for baseURL or similar patterns
            base_url_matches = re.findall(r'baseURL:["\']([^"\']+)["\']', js_content)
            if base_url_matches:
                print(f"Found baseURL in {js_file}: {base_url_matches}")
            
            # Also check for REACT_APP_BACKEND_URL pattern
            env_matches = re.findall(r'REACT_APP_BACKEND_URL:["\']([^"\']+)["\']', js_content)
            if env_matches:
                print(f"Found REACT_APP_BACKEND_URL in {js_file}: {env_matches}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_live_config()
