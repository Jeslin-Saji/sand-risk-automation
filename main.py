import ee
import os
import json
import datetime

# Authenticate using service account
service_account_info = json.loads(os.environ['EE_SERVICE_ACCOUNT'])

credentials = ee.ServiceAccountCredentials(
    service_account_info['client_email'],
    key_data=os.environ['EE_SERVICE_ACCOUNT']
)

ee.Initialize(credentials)

print("Earth Engine Initialized Successfully")

# Test simple request
# Simple dataset test
collection = ee.ImageCollection("COPERNICUS/S2_SR").limit(1)
print("Collection size:", collection.size().getInfo())

