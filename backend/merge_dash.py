with open('tmp_dashboard.py', 'r', encoding='utf-16') as f:
    orig = f.read()

idx = orig.find('else:\n    st.title("📁 Custom Telemetry CSV Ingestion & Hybrid Detection")')
if idx == -1:
    idx = orig.find('else:\n    st.title("📁 Custom Telemetry CSV Ingestion')
if idx == -1:
    idx = orig.find('else:\n    st.title')
if idx == -1:
    idx = orig.find('else:\r\n    st.title')
if idx == -1:
    idx = orig.find('else:\n    st.title("📁 Custom Telemetry CSV Ingestion & Hybrid Detection")')

view3 = orig[idx:] if idx != -1 else ''

with open('dashboard_app.py', 'r', encoding='utf-8') as f:
    cur = f.read()

idx2 = cur.find('else:\n    # VIEW 3')
if idx2 == -1:
    idx2 = cur.find('else:\r\n    # VIEW 3')

if idx2 != -1 and view3:
    new_code = cur[:idx2] + view3
    with open('dashboard_app.py', 'w', encoding='utf-8') as f:
        f.write(new_code)
    print('Merged successfully')
else:
    print('Failed to merge', idx, idx2)
