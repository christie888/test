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
#from IPython.display import display

import pandas as pd
import openpyxl

import csv

import sklearn 
from sklearn.cluster import KMeans 

import inspect



#マスク情報を使ってランプ画像を切り抜く関数
# input1 : mask_info -----------------------------------
# ruck_num, which_side, shoot_position, time_log,
# group_num, num_of_groups, lamp_num, num_of_lamps, x, y
# ------------------------------------------------------
# input2 : frames
# output : lamp_imgs
def get_lamp_imgs(mask_info, undistort_frames, param):
    side = param["get_lamp_imgs"]["img_side"]  #重心を中心とする正方形の一辺
    tmp = int(side/2)

    #ランプ画像を入れる２次元配列を用意
    lamp_imgs = []
    for i in range(len(undistort_frames)):
        lamp_imgs.append([])
    
    for i, frame in enumerate(undistort_frames):
        for row in mask_info.itertuples():
            x = int(row.x)
            y = int(row.y)
            #box = frame[y-side/2:y+side/2, x-side/2:x+side/2]
            box = frame[y-tmp:y+tmp, x-tmp:x+tmp]
            lamp_imgs[i].append(box)
            
    return lamp_imgs