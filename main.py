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
image = ee.Image("COPERNICUS/S2_SR/20220101T000239_20220101T000239_T56MNN")
print("Test Image ID:", image.getInfo()["id"])
