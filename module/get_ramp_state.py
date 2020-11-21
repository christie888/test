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
def get_ramp_state(ramp_imgs, mask_info, param):   #mask_info=["ruck_num", "which_side", "shoot_position", "time_log", "rump_num", "x", "y"]
    #フレーム毎にリストを用意し、ランプ情報を入れ込む２次元リスト
    each_rampimg_colors = []
    for i in range(len(ramp_imgs)):  #len(ramp_imgs)=10
        each_rampimg_colors.append([])

    #各ランプ画像のマスクを作成し、輝度が高い部分（しっかり光っている部分）のみ取り出してそのH,S,V各平均値を取得する
    for i, row in enumerate(ramp_imgs):
        #ランプimg一枚に対してループ----------------
        for j, img in enumerate(row): 
            #print("processing：", "frame ", i, "-", "ramp ", j)

            #各フレームの閾値処理
            ramp_gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)  #グレースケール
            ret, thresh = cv2.threshold(
                ramp_gray, 
                param["get_ramp_states"]["thresh_level2"], #閾値
                255, 
                cv2.THRESH_BINARY
                )
            #cv2.imwrite("thresh_img/img{}_{}.jpg".format(i, j), thresh)

            hsv_img = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)  #HSV変換
            color_pixels = []  #閾値処理を通過したピクセル（HSV）を格納するリスト
            for row1, row2 in zip(hsv_img, thresh):
                for color_pixel, thresh_pixel in zip(row1, row2):
                    if thresh_pixel==255:
                        color_pixels.append(color_pixel)
                    else:
                        pass
            color_pixels = np.array(color_pixels) #平均を計算しやすくするためにndarray化
            
            if len(color_pixels) >= param["get_ramp_states"]["min_n_pixels"]:   #マスクでとってきたピクセル数が一定数以上あれば処理を行うフィルター（少なすぎるのは消滅しかけと判断）
                #h_mean, s_mean, v_mean = np.mean(color_pixels, axis=0)  #H,S,Vそれぞれの平均. 輝度で敷居をかけたもののみ見ているので各範囲は狭くなるはず. しかしまだ広いので輝度の高い上位数ピクセルでとる、あるいは閾値をもっと高くして明るいところだけ取れた方が良いかも
                #kmeasnsでクラスターに分ける------
                n_clusters = param["get_ramp_states"]["n_clusters"]
                cluster = KMeans(n_clusters)
                cluster.fit(X=color_pixels)
                sorted_centers = cluster.cluster_centers_[cluster.cluster_centers_[:,0].argsort(), :]   #hの値で昇順にソート
                c = int(n_clusters/2)
                selected_h_mean = np.mean(sorted_centers[c-1:c+2, 0:1])  #各クラスター中心h値の中から高いもの、低いものを除いたものからさらに平均を取る
                #-------------------------
                #色判定--------------------
                if selected_h_mean >= param["get_ramp_states"]["green_h"][0] and selected_h_mean <= param["get_ramp_states"]["green_h"][1]:
                    each_rampimg_colors[i].append("green")
                    print("frame({}/{})__ramp({}/{})__h={}　： green".format(i+1, len(ramp_imgs), j+1, len(row), selected_h_mean))
                elif selected_h_mean >= param["get_ramp_states"]["red_h"][0] and selected_h_mean <= param["get_ramp_states"]["red_h"][1]:
                    each_rampimg_colors[i].append("red")
                    print("frame({}/{})__ramp({}/{})__h={}　： green".format(i+1, len(ramp_imgs), j+1, len(row), selected_h_mean))
                elif selected_h_mean >= param["get_ramp_states"]["blue_h"][0] and selected_h_mean <= param["get_ramp_states"]["blue_h"][1]:
                    each_rampimg_colors[i].append("blue")
                    print("frame({}/{})__ramp({}/{})__h={}　： green".format(i+1, len(ramp_imgs), j+1, len(row), selected_h_mean))
                elif selected_h_mean >= param["get_ramp_states"]["yellow_h"][0] and selected_h_mean <= param["get_ramp_states"]["yellow_h"][1]:
                    each_rampimg_colors[i].append("yellow")
                    print("frame({}/{})__ramp({}/{})__h={}　： yellow".format(i+1, len(ramp_imgs), j+1, len(row), selected_h_mean))
                else:
                    each_rampimg_colors[i].append("otehr")
                    print("frame({}/{})__ramp({}/{})__h={}　： other".format(i+1, len(ramp_imgs), j+1, len(row), selected_h_mean))
                #-------------------------
            else:
                each_rampimg_colors[i].append("No_ramp")
                print("frame({}/{})__ramp({}/{})　：No_ramp".format(i+1, len(ramp_imgs), j+1, len(row)))


    """
    #ランプ毎に情報をまとめるため、転置させる
    each_ramp_colors = []
    for i in range(len(ramp_imgs[0])):   #例）ramp_imgs...(45個、10フレーム分)　ランプ個数分のリストを入れ込むためにramp_imgs[0]を引用（何故か多い...）
        each_ramp_colors.append([])
    for each in each_rampimg_colors:
        for i, each in enumerate(each):
            each_ramp_colors[i].append(each)
    #print(each_ramp_colors)
    #例）each_ramp_colors...(10フレーム, 28個)
    """
    
    each_rampimg_colors = np.array(each_rampimg_colors)  #ndarray変換
    #print(each_rampimg_colors.shape)
    each_rampimg_colors= each_rampimg_colors.T  #転置　例）（ランプ45個、10フレーム）→（10フレーム, ランプ45個）
    #print(each_rampimg_colors.shape)
    
    """
    #状態判定
    final_results = []
    #まず基本情報を追加
    for i in range(len(each_rampimg_colors)):
        final_results.append([movie_info[0], movie_info[1], movie_info[2], movie_info[3], i])
    """


    #状態情報を追加したstateの作成---------------
    state = mask_info
    state["color"] = "a"
    state["LF"] = "a"
    # color, LFと言う名前で新しいカラムをつくる（NANで初期化される）
    # state = mask_info.reindex(columns=["ruck_num", "which_side", "shoot_position", "time_log", "x", "y", "color", "LF"])
    # ↑NANに代入できない...

    #判定結果を追加
    for i, each in enumerate(each_rampimg_colors):  #ランプ個数分繰り返し
        unique = np.unique(each)   #要素をまとめる

        #結果を mask_infoに追加していく
        if set(unique) == set(["green"]):
            state.iat[i, 6] = "green" #6はcolor
            state.iat[i, 7]  = "L" #7はLF
        elif set(unique) == set(["other"]):
            state.iat[i, 6] = "other"
            state.iat[i, 7] = "L"
        elif set(unique) == set(["green", "No_ramp"]):
            state.iat[i, 6] = "green"
            state.iat[i, 7] = "F"
        elif set(unique) == set(["other", "No_ramp"]):
            state.iat[i, 6] = "other"
            state.iat[i, 7] = "F"
        elif set(unique) == set(["No_ramp"]):
            state.iat[i, 6] = "No_ramp"
            state.iat[i, 7] = "-"
        else:
            state.iat[i, 6] = "multi_color"
            state.iat[i, 7] = "-"
    #--------------------
        

    """
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
    """
    #print(state)
    return(state)

