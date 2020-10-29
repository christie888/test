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
#input:mask_info, frames　　　output:ramp_imgs
def get_ramp_imgs(mask_info, undistort_frames, *movie_info):   #movie_infoはmainから呼び出した時だけに使う可変変数
    #重心を中心とする正方形の一辺　　　　　←横範囲はランプ間距離が近い+レールがずれにくいのでそんなに範囲取らなくて良いけど、y範囲は大きめにとった長方形で切り出すのがベターかもしれない。今後検討。
    side = 50
    tmp = int(side/2)

    # print("mask_info...:", len(mask_info))
    # print("one of a mask_info...:", len(mask_info[0]))
    # print("undistort_frames...:", len(undistort_frames))
    # print("one of a undistort_frames...:", len(undistort_frames[0]))
    # print("movie_info：", len(movie_info[0]))

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
        print("エラー：正しくramp_imgsが取得できませんでした.")


    #ランプ画像を入れる２次元配列を用意
    ramp_imgs = []
    for i in range(len(undistort_frames)):
        ramp_imgs.append([i])
    
    for i, frame in enumerate(undistort_frames):
        for each in mask_info2:
            x = int(each[5])
            y = int(each[6])
            #box = frame[y-side/2:y+side/2, x-side/2:x+side/2]
            box = frame[y-tmp:y+tmp, x-tmp:x+tmp]
            
            # #ramp_imgを画像として一応保存　呼び出し元によって処理を分ける
            # if inspect.stack()[1].filename == "make_mask_and_normal.py":
            #     cv2.imwrite("mask_ramp_imgs/{}_{}_{}_{}_{}.jpg".format(each[0],each[1],each[2],each[3],each[4]), box)
            # elif inspect.stack()[1].filename == "main.py":
            #     cv2.imwrite("current_ramp_ims/{}_{}_{}_{}_{}.jpg".format(each[0],each[1],each[2],each[3],each[4]), box)
                
            

            ramp_imgs[i].append(box)
            
    return ramp_imgs