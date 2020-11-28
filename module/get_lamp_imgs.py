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

import inspect



#マスク情報を使ってランプ画像を切り抜く関数
#input:mask_info, frames　　　output:lamp_imgs
def get_lamp_imgs(mask_info, undistort_frames, param):
    side = param["get_lamp_imgs"]["img_side"]  #重心を中心とする正方形の一辺
    tmp = int(side/2)

    #　※main.py内で事前にnormal_stateを切り分けているので、呼び出し元によって分ける必要がなくなった
    """
    #呼び出し元によって処理を分ける
    if inspect.stack()[1].filename == "make_mask_and_normal.py":
        mask_info2 = mask_info
    elif inspect.stack()[1].filename == "main.py":
        
        mask_info2 = []
        #mask_infoから今着目している動画情報に一致する箇所を抜き出す（可変引数の仕様なのかmovie_infoリストはさらにリストに入れ込まれて無駄に２次元になっているので[0]番目を指定する）
        for each in mask_info:
            if str(each[0])==str(movie_info[0][0]) and str(each[1])==str(movie_info[0][1]) and str(each[2])==str(movie_info[0][2]) and str(each[3])==str(movie_info[0][3]):
                mask_info2.append(each)
            else:
                pass
    else:
        print("エラー：正しくlamp_imgsが取得できませんでした.")
    """

    #ランプ画像を入れる２次元配列を用意
    lamp_imgs = []
    for i in range(len(undistort_frames)):
        lamp_imgs.append([])
    
    for i, frame in enumerate(undistort_frames):
        for row in mask_info.itertuples():   #mask_info...[ruck_num, which_side, shoot_position, time_log, x, y]
            x = int(row.x)
            y = int(row.y)
            #box = frame[y-side/2:y+side/2, x-side/2:x+side/2]
            box = frame[y-tmp:y+tmp, x-tmp:x+tmp]
            lamp_imgs[i].append(box)
            
    return lamp_imgs