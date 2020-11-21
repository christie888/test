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



#動画からフレームを切り出す関数
#input：動画、output：frames
def cut_frame(cap, param):
    fps = cap.get(cv2.CAP_PROP_FPS)
    
    #「interval」秒に1フレームずつ、計「num_of_frame」枚を抜き出しリストに保存
    frames = []
    start_timing = param["cut_frame"]["start_timing"]
    interval = param["cut_frame"]["interval"] 
    n_frames = param["cut_frame"]["n_frames"]
    for i in range(n_frames):
        cap.set(cv2.CAP_PROP_POS_FRAMES, round(fps * start_timing))
        ret, frame = cap.read()

        #リサイズ
        height = 1200
        width = 1600
        frame = cv2.resize(frame , ((width, height)))

        frames.append(frame)
        print(frame.shape)
        start_timing = start_timing + interval

    return frames