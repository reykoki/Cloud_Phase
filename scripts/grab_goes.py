import numpy as np
from glob import glob
import os
import pytz
from datetime import datetime, timedelta
from helper_functions import *
import s3fs
from suntime import Sun

def get_first_closest_file(band, fns, dt, sat_num):
    diff = timedelta(days=100)
    matching_band_fns = [s for s in fns if band in s]
    for fn in matching_band_fns:
        s_e = fn.split('_')[3:5]
        start = s_e[0]
        s_dt = datetime.strptime(start[1:-3], '%Y%j%H%M')
        s_dt = pytz.utc.localize(s_dt)
        if diff > abs(s_dt - dt):
            diff = abs(s_dt - dt)
            best_start = start
            best_end = s_e[1]
            best_fn = fn
    #fn_str = 'C{}_G{}_{}_{}'.format(band, sat_num, best_start, best_end)
    fn_str = 'G{}_{}_{}'.format(sat_num, best_start, best_end[:-3])
    return best_fn, fn_str

def get_additional_band_file(band, fn_str, fns):
    best_band_fn = [s for s in fns if band in s and fn_str in s]
    return best_band_fn[0]

def get_closest_file(fns, dt, sat_num, bands):
    use_fns = []
    band_init = 'C'+str(bands[0]).zfill(2)


    best_band_fn, fn_str = get_first_closest_file(band_init, fns, dt, sat_num)
    use_fns.append(best_band_fn)
    for band in bands:
        band = 'C'+str(band).zfill(2)
        best_band_fn = get_additional_band_file(band, fn_str, fns)
        use_fns.append(best_band_fn)
    return use_fns

# check if its between sunrise on the west coast and sunset on hte east coast
# check that the sun is shining on entire CONUS
def check_sunrise_sunset(dt):
    west_lon = -124.8
    west_lat = 24.5
    east_lon = -71.1
    east_lat = 45.93
    east = Sun(east_lat, east_lon)
    west = Sun(west_lat, west_lon)
    sunset = east.get_sunset_time(dt)
    sunrise = west.get_sunrise_time(dt)
    print('for the datetime {}:\nsunrise is at: {}\nsunset is at: {}'.format(dt, sunrise, sunset))
    if sunrise > sunset:
        sunset = west.get_sunset_time(dt + timedelta(days=1))
    if sunrise > dt or sunset < dt:
        raise ValueError('your request is before/after the sunrise/sunset for conus on {}'.format(dt) )
    else:
        sat_num = '16' # closer to sunset
    return sunrise, sunset

def check_sunrise_sunset_lat_lon(dt, lat, lon):
    sun = Sun(float(lat), float(lon))
    sunset = sun.get_sunset_time(dt)
    sunrise = sun.get_sunrise_time(dt)
    if sunrise > sunset:
        sunset = sun.get_sunset_time(dt + timedelta(days=1))
    print('for the location ({}, {}):\nsunrise is at: {}\nsunset is at: {}'.format(lat, lon, sunrise, sunset))
    if sunrise > dt:
        raise ValueError('your request was before sunrise at ({}, {}) on {}, set sun_check=False to grab data out side of daylight'.format(lat, lon, dt) )
    if sunset < dt:
        raise ValueError('your request was after sunset at ({}, {}) on {}, set sun_check=False to grab data out side of daylight'.format(lat, lon, dt) )

def get_filelist(dt, fs, lat, lon, sat_num, product, scope, bands):
    hr, dn, yr = get_dt_str(dt)
    full_filelist = fs.ls("noaa-goes{}/{}{}/{}/{}/{}/".format(sat_num, product, scope, yr, dn, hr))
    if sat_num == '17' and len(full_filelist) == 0:
        if yr <= 2018:
            sat_num = '16'
            print("YOU WANTED 17 BUT ITS NOT LAUNCHED")
        elif yr >= 2022:
            sat_num = '18'
        full_filelist = fs.ls("noaa-goes{}/ABI-L1b-Rad{}/{}/{}/{}/".format(sat_num, scope, yr, dn, hr))
    use_fns = get_closest_file(full_filelist, dt, sat_num, bands)
    return use_fns

def get_first_closest_file_mask(fns, dt, sat_num):
    diff = timedelta(days=100)
    for fn in fns:
        s_e = fn.split('_')[3:5]
        start = s_e[0]
        s_dt = datetime.strptime(start[1:-3], '%Y%j%H%M')
        s_dt = pytz.utc.localize(s_dt)
        if diff > abs(s_dt - dt):
            diff = abs(s_dt - dt)
            best_start = start
            best_end = s_e[1]
            best_fn = fn
    #fn_str = 'C{}_G{}_{}_{}'.format(band, sat_num, best_start, best_end)
    fn_str = 'G{}_{}_{}'.format(sat_num, best_start, best_end[:-3])
    return best_fn

def get_filelist_mask(dt, fs, lat, lon, sat_num, product="ABI-L2-CTP", scope="F"):
    hr, dn, yr = get_dt_str(dt)
    full_filelist = fs.ls("noaa-goes{}/{}{}/{}/{}/{}/".format(sat_num, product, scope, yr, dn, hr))
    use_fns = get_first_closest_file_mask(full_filelist, dt, sat_num)
    return use_fns

def download_goes(dt, lat=None, lon=None, sat_num='16', product='ABI-L1b-Rad', scope='F', check_sun=True, bands=list(range(1,4))):
    # will check sunrise for specified lat/lon
    if check_sun and lat and lon:
        check_sunrise_sunset_lat_lon(dt, lat, lon)
    # will check sunrise for CONUS
    elif check_sun:
        check_sunrise_sunset(dt)

    goes_dir = './cloud_data/goes_temp/'
    print(goes_dir)
    fs = s3fs.S3FileSystem(anon=True)
    print(fs)

    use_fns = get_filelist(dt, fs, lat, lon, sat_num, product, scope, bands)
    print(use_fns)
    use_fns_mask = get_filelist_mask(dt, fs, lat, lon, sat_num)
    use_fns.append(use_fns_mask)
    file_locs = []
    print(use_fns_mask)
    print(use_fns)
    for file_path in use_fns:
        fn = file_path.split('/')[-1]
        dl_loc = goes_dir+fn
        file_locs.append(dl_loc)
        if os.path.exists(dl_loc):
            print("{} already exists".format(fn))
        else:
            print('downloading {}'.format(fn))
            fs.get(file_path, dl_loc)
    if len(file_locs) > 0:
        return file_locs
    else:
        print('ERROR NO FILES FOUND FOR TIME REQUESTED: ', dt)

