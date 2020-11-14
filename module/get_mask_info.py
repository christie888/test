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
    #オブジェクト化-----
    nlabels, labels, stats, centroids = cv2.connectedComponentsWithStats(sum_img)
    #nlabels...ラベルの数（黒い領域も含む）
    #labels...ピクセルごとのラベリング結果（白いところが1、黒いところが0になった画像配列）
    #stats...オブジェクトのバウンディングボックス（開始点の x 座標、開始点の y 座標、幅、高さ、オブジェクトの総ピクセル数））
    #centroids...オブジェクトの重心
    #----------
    
    """
    #statsの先頭にラベルを挿入
    stats_2 = []
    for i , stat in enumerate(stats):
        stat = np.insert(stat, 0, i)
        stats_2.append(stat)
    """

    #statsをdf化
    stats_df = pd.DataFrame(stats, columns=["x", "y", "w", "h", "pixel"])

    """
    #フィルター（オブジェクトのピクセル数、オブジェクトサイズ）
    filtered_stats = []
    for i, stat in enumerate(stats_2):
        print("w: ", stat[3], "---", "h: ", stat[4])
        if (stat[5] >=100 and stat[5]<400) and (stat[3]>=15 and stat[3]<=40) and (stat[4]>=10 and stat[4]<=40):   #stat[5]...オブジェクトのピクセル数（ここの条件要検討）
            filtered_stats.append(stat)
    #print(filtered_stats)
    """

    #フィルター（入れないかもなので無くても問題なく動くように）
    delete_index = []
    tmp = 25 #ramp_imgとして切り取るときの一辺
    for row in stats_df.itertuples():  #行ごとに取得、先頭に「Index」追加
        if (row.pixel >= 100 and row.pixel < 400) and (row.w >= 15 and row.w <= 40) and (row.h >= 10 and row.h <= 40):
            delete_index.append(row.Index)
        if (row.x < tmp or row.x >1600-tmp or row.y < tmp or row.y > 1200-tmp):   #これは必須のフィルター。ramp_imgは(50,50,3)で切り取れないといけないので。さらにこのtmpをいじればフレーム内の対象とする範囲を絞ることができるのでさらなるフィルターになる。
            delete_index.append(row.Index)
    #print("delete_index", delete_index)
    stats_df = stats_df.drop(index=delete_index)
    #stats_df = stats_df.drop(index=0) #0行目には背景情報が入るだけなのでいらない
    stats_df = stats_df.reset_index(drop=True)

    """
    #フィルターを通過したものの番号をリストに入れる
    filtered_no = []
    for each in filtered_stats:
        filtered_no.append(each[0])
    """
    
    """
    #マスク情報　フィルターを通過したオブジェクトの（ランプ番号[新しく通しで振る]、ラック番号、左右情報、撮影位置番号、撮影date、重心x、重心y）
    mask_info = []
    for i, no in enumerate(filtered_no):
        x = int(centroids[no][0])
        y = int(centroids[no][1])
        mask_info.append([movie_info[0], movie_info[1], movie_info[2], movie_info[3], i, x, y])
    #print(mask_info)
    """

    #マスク情報作成
    #stats_dfをベースにmovie_infoをインサートしていく
    stats_df.insert(0, "ruck_num", movie_info[0])  #df自体が更新されるので再代入不要
    stats_df.insert(1, "which_side", movie_info[1] )
    stats_df.insert(2, "shoot_position", movie_info[2]  )
    stats_df.insert(3, "time_log", movie_info[3] )
    #いらない情報[w, h, pixel]を削除
    stats_df = stats_df.drop(columns=["w", "h", "pixel"])
    

    #csv出力作業は最後にまとめて行うのでここはパス
    """ 
    with open("mask_info.csv", "a") as f:
            writer = csv.writer(f)
            writer.writerows(mask_info)
    """

    return(stats_df)   #stats_dfをmask_infoとする
    