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
def cut_frame(cap):
    #fps
    fps = cap.get(cv2.CAP_PROP_FPS)
    
    #「interval」秒に1フレームずつ、計「num_of_frame」枚を抜き出しリストに保存
    frames = []
    timing = 0
    interval = 0.5 
    num_of_frame = 10
    for i in range(num_of_frame):
        cap.set(cv2.CAP_PROP_POS_FRAMES, round(fps * timing))
        ret, frame = cap.read()
        frames.append(frame)
        timing = timing + interval
        
    return frames




# if __name__ == "__main__":
#     cut_frame()
