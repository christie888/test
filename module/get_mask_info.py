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
    print("--------------------------------------")
    print(stats_df)
    print("--------------------------------------")
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
    tmp = 50 #ramp_imgとして切り取るときの一辺=25...で設定していたがノイズ除去の目的で大きめに取る
    for row in stats_df.itertuples():
        #フィルター１　フレームの縁からtmpだけ離れた範囲にあるか否か.
        #ramp_imgは(50,50,3)で切り取れないといけないのでこれは必須のフィルター. さらにこのtmpをいじればフレーム内の対象とする範囲を絞ることができるのでさらなるフィルターになる。
        #また撮影ポジションによる上下左右のダブり問題に関してもここの調整で対応できる.　これは重要なので後で調整方法について検討
        if (row.x < tmp or row.x >1600-tmp or row.y < tmp or row.y > 1200-tmp):
            delete_index.append(row.Index)
            continue
        #フィルター２　ピクセル数、幅、高さ
        if (
            row.pixel <= 100 or row.pixel >= 400
            or row.w <= 15 or row.w >= 40
            or row.h <= 10 or row.h >= 40
            ):
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


    return(stats_df)   #stats_dfをmask_infoとする
    