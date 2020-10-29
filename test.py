import cv2
import numpy as np
import matplotlib.pyplot as plt
#%matplotlib inline 

import os
import sys
import re
import subprocess
import datetime
import tkinter
from tkinter import messagebox

import sklearn 
from sklearn.cluster import KMeans 
import PIL   #PILのインストールはできないのに、その後継者のpillowをインストールするとimportできるようになる不思議設定
from PIL import Image
from IPython.display import display

import pandas as pd
import openpyxl

import csv

import sklearn 
from sklearn.cluster import KMeans 

import module.cut_frame
import module.undistort_frames
import module.sum_frames
import module.get_mask_info

import module.get_ramp_imgs
import module.get_ramp_state


# list = ["a","b","c","d","e"]
# print(list)
# list[0],list[1],list[2],list[3],list[4] = list[2],list[1], list[4],list[3],list[0]
# print(list)

"""
#動画名から各種情報を取得
split_name = movie.replace(".mp4", "").split("_")
ruck_num = split_name[0] #ラック番号
which_side = split_name[1] #ラックの左右情報
shoot_position = split_name[2] #撮影位置番号
time_log = split_name[3] #撮影date
movie_info = [ruck_num, which_side, shoot_position, time_log]
"""
"""
class Ruck:
    def __init__(self):
        self.left = []
        self.right = []

rucks = {
    "R06C08-A": Ruck(), 
    "R06C08-B": Ruck(), 
    "R06C08-C": Ruck()
}

for ruck_name, ruck in rucks.items():
    ruck.left.append()
    ruch_name 
    

    code = "{}_L=[]".format(order)
    print(code)
    exec(code)
    #exec("{}_R = []".format(order))
print(R06C08-A_L)

files_list = ['R06C08-C_L_0_20200826113408.mp4', 'R06C08-B_L_1_20200826113306.mp4', 'R06C08-A_L_1_20200826113102.mp4', 'R06C08-B_L_0_20200826113204.mp4', 'R06C08-A_L_0_20200826113000.mp4']

"""



# for file in file_list:
#     split_name = movie.replace(".mp4", "").split("_")
#     ruck_num = split_name[0] #ラック番号
#     which_side = split_name[1] #ラックの左右情報
#     shoot_position = split_name[2] #撮影位置番号
#     time_log = split_name[3] #撮影date
    
#     for order in order_ruck:
#         if ruck_num == order:
#             if which_side == "L":
#                 if 


# import datetime
# dt_now = datetime.datetime.now()
# print(dt_now)
# print(str(dt_now))



color_pixels = [
    [10, 20, 30, 1, 2],
    [40, 50, 60, 3, 4],
    [70, 80, 90, 5, 6],
    [100, 110, 120, 7, 8],
    [130, 140, 150, 9, 10]
]
color_pixels = np.array(color_pixels) 
raw = color_pixels[:, 1:]
print(raw)

# cluster = KMeans(n_clusters = 2)
# cluster.fit(X=raw)
# h = cluster.cluster_centers_[:, 0]
# print(h)





