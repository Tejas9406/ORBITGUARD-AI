import re
import urllib.request

url = 'https://opssat.esa.int/ops-sat-1/docs/tm_analysis.html'
req = urllib.request.Request(url, headers={'User-Agent': 'OrbitGuard-AI/1.0'})
try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        html = resp.read().decode('utf-8', errors='ignore')
        print(f"Read {len(html)} characters.")
        
        # Look for any references to uhf or telemetry or csv
        links = re.findall(r'href=["\']([^"\']+)["\']', html, re.I)
        print("Total links:", len(links))
        for l in links:
            if any(k in l.lower() for k in ['csv', 'uhf', 'telemetry', 'data', 'download', 'github', 'zenodo']):
                print("Relevant link:", l)
                
        # Also check text mentions of uhf_telemetry
        matches = re.findall(r'[^\n]*uhf_telemetry[^\n]*', html, re.I)
        print("UHF text mentions:", len(matches))
        for m in matches[:5]:
            print("  Mention:", m.strip()[:150])
except Exception as e:
    print('Failed:', e)
