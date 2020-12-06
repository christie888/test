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
#input: sum_img
#output: mask_info...["ruck_num", "which_side", "shoot_position", time_log, "x", "y", "group_num", "num_of_groups", "lamp_num", "num_of_lamps"]
def get_mask_info(sum_img, movie_info, param):
    #オブジェクト化-----
    nlabels, labels, stats, centroids = cv2.connectedComponentsWithStats(sum_img)
    #nlabels...ラベルの数（黒い領域も含む）
    #labels...ピクセルごとのラベリング結果（白いところが1、黒いところが0になった画像配列）
    #stats...オブジェクトのバウンディングボックス（開始点の x 座標、開始点の y 座標、幅、高さ、オブジェクトの総ピクセル数））
    #centroids...オブジェクトの重心
    #----------

    #statsをdf化
    stats_df = pd.DataFrame(stats, columns=["x", "y", "w", "h", "pixel"])

    #フィルター -----------------------------------
    delete_index = []
    thick = param["get_mask_info"]["remove_frame_thick"] #lamp_imgとして切り取るときの一辺=25...で設定していたがノイズ除去の目的で大きめに取る
    for row in stats_df.itertuples():
        #フィルター１　フレームの縁からtmpだけ離れた範囲にあるか否か.
        #lamp_imgは(50,50,3)で切り取れないといけないのでこれは必須のフィルター. さらにこのtmpをいじればフレーム内の対象とする範囲を絞ることができるのでさらなるフィルターになる。
        #また撮影ポジションによる上下左右のダブり問題に関してもここの調整で対応できる.　これは重要なので後で調整方法について検討
        if (row.x < thick or row.x > param["frame_w"]-thick or row.y < thick or row.y > param["frame_h"]-thick):
            delete_index.append(row.Index)
            continue
        #フィルター２　ピクセル数
        if (row.pixel <= param["get_mask_info"]["filter_n_pixels"][0] or row.pixel >= param["get_mask_info"]["filter_n_pixels"][1]):
            delete_index.append(row.Index)
            continue
        #フィルター３　幅、高さ
        if (row.w <= param["get_mask_info"]["filter_w"][0] or row.w >= param["get_mask_info"]["filter_w"][1]
            or row.h <= param["get_mask_info"]["filter_h"][0] or row.h >= param["get_mask_info"]["filter_h"][1]):
            delete_index.append(row.Index)
            continue
    #--------------------------------------------

    #print("delete_index", delete_index)
    stats_df = stats_df.drop(index=delete_index)
    #stats_df = stats_df.drop(index=0) #0行目には背景情報が入るだけなのでいらない

    #いらない情報[w, h, pixel]を削除
    stats_df = stats_df.drop(columns=["w", "h", "pixel"])  # → stats_df...["x", "y"]



    # グループに分けていく--------------
    def isInThreshold(value, center, threshold):
        return (value < center + threshold) and (center - threshold < value)
    
    _stats_df = stats_df.copy()
    _stats_df = _stats_df.values.tolist()
    tmp = None
    threshold = 100  #閾値 px

    result_groups = []   #二次元配列 
    while True:
        if len(_stats_df) == 0:
            break
        tmp = _stats_df.pop(0) #pop...指定した値の要素を取得し、元のリストから削除する
        y = tmp[1]  # 要素番号1＝y
        group = [tmp]
        for _tmp in _stats_df[:]:
            if isInThreshold(_tmp[1], y, threshold):
                group.append(_tmp)
                _stats_df.remove(_tmp)
        group = sorted(group)  # result_groupsを要素ごとにx（要素番号0）でソート
        result_groups.append(group)
    
    grouped_stats = []  #再び２次元リストに戻す. その際所属グループのナンバーとランプナンバーを要素に入れこむ.
    for i, group in enumerate(result_groups):
        for j, each in enumerate(group):
            each.insert(3,str(i)) #グループナンバー
            each.insert(4,str(len(result_groups))) #グループ数
            each.insert(5,str(j)) #グループの中でのランプナンバー
            each.insert(6,str(len(group))) #ランプ数
            grouped_stats.append(each)

    # 再度stats_dfとしてDF化
    stats_df = pd.DataFrame(grouped_stats, columns=["x", "y", "group_num", "num_of_groups", "lamp_num", "num_of_lamps"])
    #print(stats_df)
    #---------------------------------



    #マスク情報作成
    #stats_dfをベースにmovie_infoをインサートしていく
    stats_df.insert(0, "ruck_num", movie_info[0])  #df自体が更新されるので再代入不要
    stats_df.insert(1, "which_side", movie_info[1] )
    stats_df.insert(2, "shoot_position", movie_info[2]  )
    stats_df.insert(3, "time_log", movie_info[3] )


    # ---------------------------------
    # mask_info：   ["ruck_num", "which_side", "shoot_position", time_log, "x", "y", "group_num", "num_of_groups", "lamp_num", "num_of_lamps"]
    # ---------------------------------
    return(stats_df)   #stats_dfをmask_infoとする
    