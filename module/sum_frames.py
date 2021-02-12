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


#補正後フレームから集合画像を作る関数
#input:undistort_frame、output:sum
def sum_frames(undistort_frames, param):
    #グレースケール
    frames_gray = []
    for undistort_frame in undistort_frames:
        frame_gray = cv2.cvtColor(undistort_frame, cv2.COLOR_RGB2GRAY)
        frames_gray.append(frame_gray)
    
    #各フレームの閾値処理
    thresholds = []
    for frame_gray in frames_gray:
        ret, thresh = cv2.threshold(
            frame_gray,
            param["sum_frames"]["thresh_level1"],  #閾値
            255,
            cv2.THRESH_BINARY
            )
        thresholds.append(thresh)
    
    #各フレームの膨張&収縮 ←通常の膨張処理にした方が良いのか、カーネルは幾つにするのか、など検討の必要あり
    closings = []
    kernel = np.ones((param["sum_frames"]["kernel_size"], param["sum_frames"]["kernel_size"]), np.uint8) 
    for thresh in thresholds:
        closing = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)  #closing処理
        closings.append(closing)
    
    #closingsの重ね画像
    sum_closings = sum(closings)
    
    #dilatesの10フレームをピクセルごとに足し算する。
    #その結果、フレームの黒い部分は0のまま、白い部分は1以上の数字を持つことになる
    #この1以上の部分を白（255）にする
    sum_img = np.zeros((param["frame_h"], param["frame_w"]), dtype = "uint8") # 合成画像用の変数を作成
    for i,row in enumerate(sum_closings):
        for j, a in enumerate(row):
            if a != 0:
                sum_img[i][j] = 255
    
    return(sum_img)