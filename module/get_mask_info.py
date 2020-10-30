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





#sum_imgをフィルタリングしてマスク情報を取得する関数
#input:sum_img、output:mask_info
def get_mask_info(sum_img, movie_info):
    #オブジェクト化してかたまり単位で認識する
    #オブジェクト処理...connectedComponentsWithStats()
    nlabels, labels, stats, centroids = cv2.connectedComponentsWithStats(sum_img)
    #nlabels...ラベルの数（黒い領域も含む）
    #labels...ピクセルごとのラベリング結果（白いところが1、黒いところが0になった画像配列）
    #stats...オブジェクトのバウンディングボックス（開始点の x 座標、開始点の y 座標、幅、高さ、オブジェクトの総ピクセル数））
    #centroids...オブジェクトの重心

    #print(movie_info)
    #cv2.imwrite("sum_img.jpg", sum_img)
    #print("nlabels（元）：", nlabels)
    
    #statsの先頭にラベルを挿入
    stats_2 = []
    for i , stat in enumerate(stats):
        stat = np.insert(stat, 0, i)
        stats_2.append(stat)
        
    #フィルター（オブジェクトのピクセル数、オブジェクトサイズ）
    filtered_stats = []
    for i, stat in enumerate(stats_2):
        print("w: ", stat[3], "---", "h: ", stat[4])
        if (stat[5] >=100 and stat[5]<400) and (stat[3]>=15 and stat[3]<=40) and (stat[4]>=10 and stat[4]<=40):   #stat[5]...オブジェクトのピクセル数（ここの条件要検討）
            filtered_stats.append(stat)
    #print(filtered_stats)
    
    #フィルターを通過したものの番号をリストに入れる
    filtered_no = []
    for each in filtered_stats:
        filtered_no.append(each[0])
    
    #マスク情報　フィルターを通過したオブジェクトの（ランプ番号[新しく通しで振る]、ラック番号、左右情報、撮影位置番号、撮影date、重心x、重心y）
    mask_info = []
    for i, no in enumerate(filtered_no):
        x = int(centroids[no][0])
        y = int(centroids[no][1])
        mask_info.append([movie_info[0], movie_info[1], movie_info[2], movie_info[3], i, x, y])
    #print(mask_info)
    
    #mask_infoをcsv出力
    # with open("mask_info.csv", "w") as f:
    #     writer = csv.writer(f)
    #     writer.writerows(mask_info)

    # if i == 0:
    #     #正常状態記録をcsv出力
    #     with open("mask_info.csv", "w") as f:
    #         writer = csv.writer(f)
    #         writer.writerows(mask_info)
    # else:
    #     #正常状態記録をcsv出力
    #     with open("mask_info.csv", "a") as f:
    #         writer = csv.writer(f)
    #         writer.writerows(mask_info)
    with open("mask_info.csv", "a") as f:
            writer = csv.writer(f)
            writer.writerows(mask_info)
        
    return(mask_info)
    