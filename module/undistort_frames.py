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




#framesに補正をかける関数
#input:frames、output:undistort_frames
def undistort_frames(frames):
    
    #補正用のキャリブレーション取得
    camera_mat, dist_coef_L = [], []
    param_path = './param/' + '8' + '/'  #ひとまず8番カメラのみに対応しているが、最終的には何番のカメラで撮影したのか特定し自動で割り振らなければいけない
    camera_mat = np.loadtxt(param_path + 'K.csv', delimiter=',')
    dist_coef = np.loadtxt(param_path + 'd.csv', delimiter=',')
    #print("K = \n", camera_mat)
    #print("d = ", dist_coef.ravel())
    
    undistort_frames = []
    for frame  in frames:
        undistort_frame = cv2.undistort(frame, camera_mat, dist_coef)
        #pltshow(undistort_frame)
        undistort_frames.append(undistort_frame)
        #print(frame.shape)
        #print(undistort_frame.shape)
    
    return(undistort_frames)