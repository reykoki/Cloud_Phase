import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import sys
import numpy as np
import skimage
from glob import glob
import os
import time
import pytz
from datetime import datetime, timedelta
import wget
import json
sys.path.insert(1, './scripts')
import pyproj
from helper_functions import *
from PIL import Image, ImageOps
import warnings
warnings.filterwarnings('ignore')
from IPython.display import clear_output
from satpy.writers import get_enhanced_image
import s3fs
from suntime import Sun
from grab_goes import *
from helper_functions import *
from satpy import Scene
from pyresample import create_area_def


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

def get_proj():
    lcc_proj = ccrs.LambertConformal(central_longitude=262.5,
                                     central_latitude=38.5,
                                     standard_parallels=(38.5, 38.5),
                                     globe=ccrs.Globe(semimajor_axis=6371229,
                                                      semiminor_axis=6371229))
    return lcc_proj





# get the Satpy Scene object
def get_scn(fns, to_load, extent, res=3000, proj=get_proj(), reader='abi_l1b', print_info=False):
    scn = Scene(reader=reader, filenames=fns)
    scn.load(to_load, generate=False)
    my_area = create_area_def(area_id='my_area',
                              projection=proj,
                              resolution=res,
                              area_extent=extent
                              )
    if print_info:
        print("Available channels in the Scene object:\n", scn.available_dataset_names())
        print("\nAvailable composites:\n", scn.available_composite_names())
        print("\nArea definitition:\n",my_area)
    new_scn = scn.resample(my_area) # resamples datasets and resturns a new scene object
    return new_scn

def split_and_save(full_image, full_truth, fn_head, img_size=256):
    yr = fn_head.split('s')[1][0:4]
    n_row = int(full_image.shape[0]/img_size)
    n_col = int(full_image.shape[1]/img_size)
    full_image = full_image[0:int(n_row*img_size),0:int(n_col*img_size)][:]
    full_truth = full_truth[0:int(n_row*img_size),0:int(n_col*img_size)][:]
    fn_list = []
    for row in range(n_row):
        for col in range(n_col):
            data = full_image[int(row*img_size):int((row+1)*img_size),int(col*img_size):int((col+1)*img_size)][:]
            truth = full_truth[int(row*img_size):int((row+1)*img_size),int(col*img_size):int((col+1)*img_size)][:]
            fn = '{}_{}_{}.tif'.format(fn_head, row, col)
            density = "Light"
            skimage.io.imsave('./cloud_data/data/{}/{}'.format(yr, fn), data)
            skimage.io.imsave('./cloud_data/truth/{}/{}'.format(yr, fn), truth)
            fn_list.append(fn)

    return fn_list

def get_one_hot(not_hot):
    binary = np.take(np.eye(5), not_hot, axis=1)
    binary = binary[1:,:,:]
    binary = np.einsum('ijk->jki', binary)
    return binary


res = 2000 # 5km resolution
extent = [-2.4e6, -1.6e6, 2.72e6, 1.472e6]
cloud_mask = ["Phase"]
composite = ["cimss_true_color_sunz_rayleigh"]


def get_RGB(scn, composite):
    RGB = get_enhanced_image(scn[composite]).data.compute().data
    RGB = np.einsum('ijk->jki', RGB)
    RGB[np.isnan(RGB)] = 0
    return RGB

def create_dataset(dt, sat_fns):
    scn = get_scn(sat_fns[:-1], composite, extent, res) # get satpy scn object
    conus_crs = scn[composite[0]].attrs['area'].to_cartopy_crs()
    cloud_scn = get_scn([sat_fns[-1]], cloud_mask, extent, res, reader='abi_l2_nc')
    RGB = get_RGB(scn, "cimss_true_color_sunz_rayleigh" )
    cloud_phase = cloud_scn['Phase'].compute().data
    cloud_phase[cloud_phase==255] = 0 # 255 seems like the number used for where radiance == nan
    one_hot_mask = get_one_hot(cloud_phase) # from the scene object, extract RGB data for plotting
    fn_head = sat_fns[0].split('C01_')[-1].split('.')[0].split('_c2')[0]
    tif_fns = split_and_save(RGB, one_hot_mask, fn_head)


def times_sunrise_to_sunset(dt):
    west_lon = -124.8
    west_lat = 24.5
    east_lon = -71.1
    east_lat = 45.93
    east = Sun(east_lat, east_lon)
    west = Sun(west_lat, west_lon)
    sunset = east.get_sunset_time(dt)
    sunrise = west.get_sunrise_time(dt)
    if sunrise > sunset:
        sunset = west.get_sunset_time(dt + timedelta(days=1))
    times = []
    new_time = sunrise

    while new_time < sunset:
        times.append(new_time)
        new_time = times[-1] + timedelta(hours=1)
    return times

def main():
    yr = '2023'
    dns = np.arange(93,365)
    for dn in dns:
        dn_dt = pytz.utc.localize(datetime.strptime("{}{}".format(yr,dn), '%Y%j'))
        times = times_sunrise_to_sunset(dn_dt)
        for dt in times:
            try:
                sat_fns = download_goes(dt)
                check_fns = glob("cloud_data/goes_temp/*nc")
                if len(check_fns) == 4:
                    create_dataset(dt, sat_fns)
                for sat_fn in check_fns:
                    check_fns = glob("cloud_data/goes_temp/*nc")
                    os.remove(sat_fn)
            except Exception as e:
                print(e)
                



if __name__ == '__main__':
    main()

