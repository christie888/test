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


#framesに補正をかける関数
#input:frames、output:undistort_frames
def undistort_frames(frames, movie_info):
    #補正用パラメータ取得
    cam_num = movie_info[4]
    camera_mat, dist_coef_L = [], []
    param_path = './param/{}/'.format(cam_num)  #ひとまず8番カメラのみに対応しているが、最終的には何番のカメラで撮影したのか特定し自動で割り振らなければいけない
    camera_mat = np.loadtxt(param_path + 'K.csv', delimiter=',')
    dist_coef = np.loadtxt(param_path + 'd.csv', delimiter=',')
    #print("K = \n", camera_mat)
    #print("d = ", dist_coef.ravel())
    
    undistort_frames = []
    for frame  in frames:
        undistort_frame = cv2.undistort(frame, camera_mat, dist_coef)
        undistort_frames.append(undistort_frame)
    
    return(undistort_frames)