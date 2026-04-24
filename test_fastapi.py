import os
import sys

sys.path.append(os.path.abspath('backend'))
import main
from fastapi.testclient import TestClient

client = TestClient(main.app)
response = client.get('/api/system/keys/health')
print('Status Code:', response.status_code)
print('Response body:', response.text)
