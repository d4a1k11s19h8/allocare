import os
import sys

# Remove existing data.json
if os.path.exists('data.json'):
    os.remove('data.json')

# Import and trigger the seed which generates the file
from data_store_local import store
store.seed_demo_data()
print("Successfully generated data.json!")
