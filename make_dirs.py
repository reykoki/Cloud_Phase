import os
import glob

# truth
#   2018
#     Light
#     Medium
#     Heavy

root_dir = './cloud_data/'

if len(os.listdir(root_dir)) == 0:
    data_type = ['truth/', 'data/']
    yrs = ['2018/', '2019/', '2020/', '2021/', '2022/', '2023/', '2024/']

    for dt in data_type:
        for yr in yrs:
            pth = root_dir + dt + yr
            if not os.path.exists(pth):
                os.makedirs(pth)

    other = [root_dir+'goes_temp/']
    for directory in other:
        if not os.path.exists(directory):
            os.makedirs(directory)
    def list_files(root_dir):
        for root, dirs, files in os.walk(root_dir):
            level = root.replace(root_dir, '').count(os.sep)
            indent = ' ' * 4 * (level)
            print('{}{}/'.format(indent, os.path.basename(root)))
            subindent = ' ' * 4 * (level + 1)
            for f in files:
                print('{}{}'.format(subindent, f))
    list_files(root_dir)
else:
    print("DIRECTORY IS NOT EMPTY \n {}".format(root_dir))

