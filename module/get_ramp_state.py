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
import glob

from IPython.display import display

import pandas as pd
import openpyxl

import csv

import sklearn 
from sklearn.cluster import KMeans 

import module.cut_frame
import module.undistort_frames
import module.sum_frames
import module.get_mask_info
import module.get_ramp_imgs
import module.get_ramp_state

import inspect

#メール送信
import smtplib


#ランプ画像からその状態情報（色、点滅情報）を抽出する関数、また結果はcsvで出力
#関数内には色を判定する機能も書き込む
#input:ramp_imgs、output:ramp_states（ランプ毎の色、点滅状態情報）
def get_ramp_state(ramp_imgs, movie_info):

    #フレーム毎にリストを用意し、ランプ情報を入れ込む２次元リスト
    color_results = []
    for i in range(len(ramp_imgs)):
        color_results.append([])

    #各ランプ画像のマスクを作成し、輝度が高い部分（しっかり光っている部分）のみ取り出してそのH,S,V各平均値を取得する
    for i, raw in enumerate(ramp_imgs):
        for j, img in enumerate(raw):
            print("processing：", "frame ", i, "-", "ramp ", j)
            if j == 0:
                pass
            else:
                #グレースケール
                ramp_gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
                #各フレームの閾値処理
                ret, thresh = cv2.threshold(ramp_gray, 120, 255, cv2.THRESH_BINARY)
                #cv2.imwrite("thresh_img/img{}_{}.jpg".format(i, j), thresh)
                
                #HSVに変換
                hsv_img = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
                
                color_pixels = []  #その画像の中での該当ピクセルHSV
                for k, (raw1, raw2) in enumerate(zip(hsv_img, thresh)):
                    for l, (color_pixel, thresh_pixel) in enumerate(zip(raw1, raw2)):
                        if thresh_pixel==255:
                            color_pixels.append(color_pixel)
                        else:
                            pass
                color_pixels = np.array(color_pixels) #平均を計算しやすくするためにndarray化
                
                if len(color_pixels) >= 10:   #マスクでとってきたピクセル数が一定数以上あれば処理を行うフィルター（少なすぎるのは消滅しかけと判断）
                    #print(len(color_pixels))
                    #print(type(color_pixels))

                    h_mean, s_mean, v_mean = np.mean(color_pixels, axis=0)  #H,S,Vそれぞれの平均　　輝度で敷居をかけたもののみ見ているので各範囲は狭くなるはず。しかしまだ広いので輝度の高い上位数ピクセルでとる、あるいは閾値をもっと高くして明るいところだけ取れた方が良いかも
                    if h_mean >= 40 and h_mean <= 80:
                        #print(mean, "：green")
                        color_results[i].append("green")
                    else:
                        #print(mean, "：other")
                        color_results[i].append("otehr")


                    # #kmeasnsで３クラスターに分ける------
                    #color_pixels = color_pixels.reshape((color_pixels.shape[0] * color_pixels.shape[1], 3))
                    cluster = KMeans(n_clusters = 5)
                    cluster.fit(X=color_pixels)
                    sorted_centers = cluster.cluster_centers_[cluster.cluster_centers_[:,0].argsort(), :]   #hの値で昇順にソート
                    print(sorted_centers)
                    print(np.mean(sorted_centers[1:4, 0:1]))
                    #----------
                    
                    
                else:
                    #print("No_ramp")
                    color_results[i].append("No_ramp")
    


    #ランプ毎に情報をまとめた２次元リストに変更
    ramp_info = []
    for i in range(len(ramp_imgs[0])):   #例）ramp_imgs...(28個、10フレーム分)　ランプ個数分のリストを入れ込むためにramp_imgs[0]を引用（何故か多い...）
        ramp_info.append([])
    for one_frame_info in color_results:
        for i, each in enumerate(one_frame_info):
            ramp_info[i].append(each)
    #print(ramp_info)
    #例）ramp_info...(10フレーム, 28個)
    


    #状態判定
    final_results = []
    #まず基本情報を追加
    for i in range(len(ramp_info)):
        final_results.append([movie_info[0], movie_info[1], movie_info[2], movie_info[3], i])
    #判定結果を追加
    for i, each in enumerate(ramp_info):
        unique = np.unique(each)   #要素をまとめる
        #print("unique：", unique)
        if set(unique) == set(["green"]):
            final_results[i].extend(["green", "L"])
        elif set(unique) == set(["other"]):
            final_results[i].extend(["other", "L"])
        elif set(unique) == set(["green", "No_ramp"]):
            final_results[i].extend(["green", "F"])
        elif set(unique) == set(["other", "No_ramp"]):
            final_results[i].extend(["other", "F"])
        elif set(unique) == set(["No_ramp"]):
            final_results[i].extend(["No_ramp", "-"])
        else:
            final_results[i].extend(["検知エラー", "-"])

    # print("ramp_imgs...:", len(ramp_imgs))
    # print("one of a ramp_imgs...:", len(ramp_imgs[0]))
    # print("ramp_info...:", len(ramp_info))
    # print("one of a ramp_info...:", len(ramp_info[0]))
    # print("final_results...：", len(final_results))
    # print("one of a final_results...：", len(final_results[0]))


    #fiinal_resultsを正常状態記録としてcsv出力（呼び出し元によってどっちのcsvに出力するか分ける）
    if inspect.stack()[1].filename == "make_mask_and_normal.py":
        with open("normal_state.csv", "a") as f:
            writer = csv.writer(f)
            writer.writerows(final_results)
    elif inspect.stack()[1].filename == "main.py":
        # #↓current_stateの内容はリストのまま使うし、resultのcsvにも踏襲されているのでわざわざ出力しなくて良い
        # with open("current_state.csv", "a") as f:
        #     writer = csv.writer(f)
        #     writer.writerows(final_results)
        pass
    else:
        print("エラー：正しくcsvに保存されていません")

    #print(final_results)
    return(final_results)

