"""Build DEM mosaics from Copernicus GLO-90 (AWS open data) via HTTP range reads of COG overviews.
Copernicus DEM: © DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018 provided under COPERNICUS by the EU and ESA."""
import os
import sys, numpy as np, rasterio, concurrent.futures as cf
from rasterio.enums import Resampling
def tile_url(lat, lon):
    ns = 'N' if lat >= 0 else 'S'; ew = 'E' if lon >= 0 else 'W'
    name = f"Copernicus_DSM_COG_30_{ns}{abs(lat):02d}_00_{ew}{abs(lon):03d}_00_DEM"
    return f"/vsicurl/https://copernicus-dem-90m.s3.amazonaws.com/{name}/{name}.tif"
def mosaic(lat0, lat1, lon0, lon1, px_per_deg, out):
    H = (lat1-lat0)*px_per_deg; W = (lon1-lon0)*px_per_deg
    arr = np.zeros((H, W), np.float32)
    def get(lat, lon):
        try:
            with rasterio.open(tile_url(lat, lon)) as ds:
                w = px_per_deg if ds.width >= 1200 else px_per_deg  # GLO-90 tiles above 50deg are narrower; not relevant here
                d = ds.read(1, out_shape=(px_per_deg, px_per_deg), resampling=Resampling.average)
                return lat, lon, d
        except Exception:
            return lat, lon, None
    jobs = [(la, lo) for la in range(lat0, lat1) for lo in range(lon0, lon1)]
    n = 0
    with cf.ThreadPoolExecutor(16) as ex:
        for lat, lon, d in ex.map(lambda j: get(*j), jobs):
            if d is not None:
                r = (lat1-1-lat)*px_per_deg; c = (lon-lon0)*px_per_deg
                arr[r:r+px_per_deg, c:c+px_per_deg] = d; n += 1
    np.save(out, arr); print(out, arr.shape, 'tiles', n, 'max', arr.max())
if __name__ == '__main__':
    D = os.environ.get('IRAM_WORK', '/home/user/iram-work') + '/data/dem/'
    mosaic(10, 34, 32, 62, 150, D+'arabia_150ppd.npy')      # whole peninsula ~740 m
    mosaic(16, 21, 50, 57, 600, D+'dhofar_600ppd.npy')      # Dhofar / Shisr ~185 m
    mosaic(28, 31, 34, 37, 1200, D+'wadirum_1200ppd.npy')   # Wadi Rum 90 m
