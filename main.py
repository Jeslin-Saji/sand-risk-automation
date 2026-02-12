import ee
import os
import json
import datetime

# ======================================================
# AUTHENTICATION
# ======================================================

service_account_info = json.loads(os.environ['EE_SERVICE_ACCOUNT'])

credentials = ee.ServiceAccountCredentials(
    service_account_info['client_email'],
    key_data=os.environ['EE_SERVICE_ACCOUNT']
)

ee.Initialize(credentials)
print("Earth Engine Initialized")

# ======================================================
# DATE LOGIC (AUTO UPDATES DAILY)
# ======================================================

end = datetime.datetime.utcnow()
start = end - datetime.timedelta(days=30)

END = ee.Date(end)
START = ee.Date(start)

SCALE = 30

# ======================================================
# LOAD ASSETS (UPDATE IF PATHS DIFFER)
# ======================================================

AOI = ee.FeatureCollection('projects/sand-risk-project/assets/Sand_AOI')
ROADS = ee.FeatureCollection('projects/sand-risk-project/assets/Road_1')

# ======================================================
# SAFE MEDIAN FUNCTION
# ======================================================

def safe_median(collection, band):
    filtered = collection.select(band)
    return ee.Image(
        ee.Algorithms.If(
            filtered.size().gt(0),
            filtered.median().rename(band),
            ee.Image.constant(0).rename(band)
        )
    )

# ======================================================
# SENTINEL-2 NDVI + NDSI
# ======================================================

s2 = (
    ee.ImageCollection('COPERNICUS/S2_SR')
    .filterBounds(AOI)
    .filterDate(START, END)
    .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 40))
)

def add_ndvi(img):
    return img.normalizedDifference(['B8','B4']).rename('NDVI')

def add_ndsi(img):
    return img.normalizedDifference(['B11','B8']).rename('NDSI')

ndvi_col = s2.map(add_ndvi)
ndsi_col = s2.map(add_ndsi)

ndvi_now = safe_median(ndvi_col, 'NDVI').clip(AOI)
ndsi_now = safe_median(ndsi_col, 'NDSI').clip(AOI)

# ======================================================
# SENTINEL-1 VV
# ======================================================

s1 = (
    ee.ImageCollection('COPERNICUS/S1_GRD')
    .filterBounds(AOI)
    .filterDate(START, END)
    .filter(ee.Filter.eq('instrumentMode','IW'))
    .filter(ee.Filter.listContains('transmitterReceiverPolarisation','VV'))
    .select('VV')
)

vv_now = safe_median(s1, 'VV').clip(AOI)

# ======================================================
# NORMALIZATION
# ======================================================

ndvi_norm = ndvi_now.unitScale(-0.2,0.6).clamp(0,1)
ndsi_norm = ndsi_now.unitScale(0,0.6).clamp(0,1)
vv_norm   = vv_now.unitScale(-25,-5).clamp(0,1)

# ======================================================
# FINAL SAND RISK SCORE
# ======================================================

sand_risk = (
    ndvi_norm.multiply(-0.35)
    .add(ndsi_norm.multiply(0.40))
    .add(vv_norm.multiply(0.25))
    .rename('SandRisk')
    .clamp(0,1)
)

# ======================================================
# ROAD RISK VECTOR
# ======================================================

road_risk_vector = sand_risk.reduceRegions(
    collection=ROADS,
    reducer=ee.Reducer.mean(),
    scale=SCALE,
    tileScale=8
)

# Add Risk Class
LOW = 0.35
MED = 0.60

def classify(feature):
    raw_risk = feature.get('mean')

    risk = ee.Number(
        ee.Algorithms.If(
            ee.Algorithms.IsEqual(raw_risk, None),
            0,
            raw_risk
        )
    )

    centroid = feature.geometry().centroid()

    risk_class = ee.String(
        ee.Algorithms.If(
            risk.lte(LOW), 'Low',
            ee.Algorithms.If(
                risk.lte(MED), 'Medium', 'High'
            )
        )
    )

    return ee.Feature(None, {
        'Road': feature.get('Road'),
        'SandRisk': risk,
        'RiskClass': risk_class,
        'Latitude': centroid.coordinates().get(1),
        'Longitude': centroid.coordinates().get(0)
    })


road_risk_vector = road_risk_vector.map(classify)

# ======================================================
# TOP 10 ROADS
# ======================================================

top10 = road_risk_vector.sort('SandRisk', False).limit(10)

# ======================================================
# EXPORT FULL ROAD RISK CSV
# ======================================================

task1 = ee.batch.Export.table.toCloudStorage(
    collection=road_risk_vector,
    description='RoadRisk_Current',
    bucket='sand-risk-bucket-jeslin',  # <-- your bucket name
    fileNamePrefix='RoadRisk_Current',
    fileFormat='CSV'
)


task1.start()
print("Road Risk CSV Export Started")

# ======================================================
# EXPORT TOP 10 CSV
# ======================================================

task2 = ee.batch.Export.table.toCloudStorage(
    collection=top10,
    description='Top10_Current',
    bucket='sand-risk-bucket-jeslin',  # <-- your bucket name
    fileNamePrefix='Top10_Current',
    fileFormat='CSV'
)


task2.start()
print("Top 10 CSV Export Started")


