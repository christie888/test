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

import collections


#ランプ画像からその状態情報（色、点滅情報）を抽出する関数、また結果はcsvで出力
#関数内には色を判定する機能も書き込む
#input:ramp_imgs、output:ramp_states（ランプ毎の色、点滅状態情報）
def get_ramp_state(ramp_imgs, mask_info, param):   #mask_info=["ruck_num", "which_side", "shoot_position", "time_log", "rump_num", "x", "y"]
    #フレーム毎にリストを用意し、ランプ情報を入れ込む２次元リスト
    each_rampimg_colors = []
    for i in range(len(ramp_imgs)):  #len(ramp_imgs)=10
        each_rampimg_colors.append([])
    # ターミナルでの色確認用に selected_h_mean を格納するリスト
    selected_h_means = []
    for i in range(len(ramp_imgs)):
        selected_h_means.append([])


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
                n_clusters = param["get_ramp_states"]["n_clusters"] #クラスター数
                cluster = KMeans(n_clusters)
                cluster.fit(X=color_pixels)
                sorted_centers = cluster.cluster_centers_[cluster.cluster_centers_[:,0].argsort(), :]   #hの値で昇順にソート
                c = int(n_clusters/2)
                selected_h_mean = np.mean(sorted_centers[c-1:c+2, 0:1])  #各クラスター中心h値の中から高いもの、低いものを除いたものからさらに平均を取る
                #-------------------------

                #色判定--------------------
                class Color:  # ターミナル出力色の定義
                    GREEN          = '\033[32m'#(文字)緑
                    RED            = '\033[31m'#(文字)赤
                    YELLOW         = '\033[33m'#(文字)黄
                    BLUE           = '\033[34m'#(文字)青
                    RESET          = '\033[0m'#全てリセット
                    
                # Hue180°色相環の度数で色が異なるがpythonでは度数を256（8ビット換算）して用いられる。その変換はコード内で行うのでjsonには180°色相環の値をそのまま用いる。
                red_h_min = param["get_ramp_states"]["red_h"][0] *(256/180)
                red_h_max = param["get_ramp_states"]["red_h"][1] *(256/180)
                yellow_h_min = param["get_ramp_states"]["yellow_h"][0] *(256/180)
                yellow_h_max = param["get_ramp_states"]["yellow_h"][1] *(256/180)
                green_h_min = param["get_ramp_states"]["green_h"][0] *(256/180)
                green_h_max = param["get_ramp_states"]["green_h"][1] *(256/180)
                blue_h_min = param["get_ramp_states"]["blue_h"][0] *(256/180)
                blue_h_max = param["get_ramp_states"]["blue_h"][1] *(256/180)
                if selected_h_mean >= green_h_min and selected_h_mean <= green_h_max:
                    each_rampimg_colors[i].append("green")
                    selected_h_means[i].append(int(selected_h_mean *(180/256))) # 元のHue値に戻したものを出力したいのでまたかける
                    #print("frame({}/{})__ramp({}/{})__h={}　： {}green{}".format(i+1, len(ramp_imgs), j+1, len(row), int(selected_h_mean), Color.GREEN, Color.RESET))
                elif selected_h_mean >= red_h_min and selected_h_mean <= red_h_max:
                    each_rampimg_colors[i].append("red")
                    selected_h_means[i].append(int(selected_h_mean *(180/256)))
                    #print("frame({}/{})__ramp({}/{})__h={}　： {}red{}".format(i+1, len(ramp_imgs), j+1, len(row), int(selected_h_mean), Color.RED, Color.RESET))
                elif selected_h_mean >= blue_h_min and selected_h_mean <= blue_h_max:
                    each_rampimg_colors[i].append("blue")
                    selected_h_means[i].append(int(selected_h_mean *(180/256)))
                    #print("frame({}/{})__ramp({}/{})__h={}　： {}blue{}".format(i+1, len(ramp_imgs), j+1, len(row), int(selected_h_mean), Color.BLUE, Color.RESET))
                # elif selected_h_mean >= yellow_h_min and selected_h_mean <= yellow_h_max:
                #     each_rampimg_colors[i].append("yellow")
                #     selected_h_means[i].append(selected_h_mean)
                #     print("frame({}/{})__ramp({}/{})__h={}　： {}yellow{}".format(i+1, len(ramp_imgs), j+1, len(row), int(selected_h_mean), Color.YELLOW, Color.RESET))
                else:
                    each_rampimg_colors[i].append("other")
                    selected_h_means[i].append(int(selected_h_mean *(180/256)))
                    #print("frame({}/{})__ramp({}/{})__h={}　： other".format(i+1, len(ramp_imgs), j+1, len(row), int(selected_h_mean)))
                #-------------------------
            else:
                each_rampimg_colors[i].append("No_ramp")
                selected_h_means[i].append("---")
                #print("frame({}/{})__ramp({}/{})　：No_ramp".format(i+1, len(ramp_imgs), j+1, len(row)))


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
    #print("---------------------------------")
    each_rampimg_colors = np.array(each_rampimg_colors)  #ndarray変換
    selected_h_means = np.array(selected_h_means)
    #print(each_rampimg_colors.shape)
    #print(selected_h_means.shape)
    #print(selected_h_means)
    each_rampimg_colors= each_rampimg_colors.T  #転置　例）（10フレーム, ランプ45個）→（ランプ45個、10フレーム)
    selected_h_means = selected_h_means.T
    #print(each_rampimg_colors.shape)
    #print(selected_h_means.shape)
    #print("---------------------------------")


    # ターミナルでの確認用
    for i, (row_c, row_h) in enumerate(zip(each_rampimg_colors, selected_h_means)):
        print("ramp({}/{})--------------------".format(i, len(each_rampimg_colors)-1))
        for j ,(color, hue) in enumerate(zip(row_c, row_h)):
            if color == "green":
                print("frame({}/{})__h={}　： {}green{}".format(j+1, len(row_c), hue, Color.GREEN, Color.RESET))
            elif color == "red":
                print("frame({}/{})__h={}　： {}red{}".format(j+1, len(row_c), hue, Color.RED, Color.RESET))
            elif color == "blue":
                print("frame({}/{})__h={}　： {}blue{}".format(j+1, len(row_c), hue, Color.BLUE, Color.RESET))
            elif color == "other":
                print("frame({}/{})__h={}　： other".format(j+1, len(row_c), hue))
            else:
                print("frame({}/{})： No_ramp".format(j+1, len(row_c)))


    
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
        # unique = np.unique(each)   #要素をまとめる
        # 結果を mask_infoに追加していく
        # 誤検知で他の色がフレームに入ってしまうこともある. 最も多く検知した色をそのランプの色とする.
        if "No_ramp" in each:
            each = [temp for temp in each if temp != "No_ramp"]  #No_ramp以外
            if len(each) == 0:
                state.iat[i, 6] = "OFF" #6はcolor
                state.iat[i, 7]  = "-" #7はLF
            else:
                counter = collections.Counter(each)
                most = counter.most_common()
                state.iat[i, 6] = most[0][0]
                state.iat[i, 7]  = "F"
        else:
            counter = collections.Counter(each)
            most = counter.most_common()
            state.iat[i, 6] = most[0][0]
            state.iat[i, 7]  = "L"
    print(state)

    """
        # green
        if set(unique) == set(["green"]): 
            state.iat[i, 6] = "green" #6はcolor
            state.iat[i, 7]  = "L" #7はLF
        elif set(unique) == set(["green", "No_ramp"]):
            state.iat[i, 6] = "green"
            state.iat[i, 7] = "F"
        # red
        if set(unique) == set(["red"]):
            state.iat[i, 6] = "red"
            state.iat[i, 7]  = "L"
        elif set(unique) == set(["red", "No_ramp"]):
            state.iat[i, 6] = "red"
            state.iat[i, 7] = "F"
        # yellow
        if set(unique) == set(["yellow"]):
            state.iat[i, 6] = "yellow"
            state.iat[i, 7]  = "L"
        elif set(unique) == set(["yellow", "No_ramp"]):
            state.iat[i, 6] = "yellow"
            state.iat[i, 7] = "F"
        # blue
        if set(unique) == set(["blue"]):
            state.iat[i, 6] = "blue"
            state.iat[i, 7]  = "L"
        elif set(unique) == set(["blue", "No_ramp"]):
            state.iat[i, 6] = "blue"
            state.iat[i, 7] = "F"
        # 未定義色
        elif set(unique) == set(["other"]):
            state.iat[i, 6] = "other"
            state.iat[i, 7] = "L"
        elif set(unique) == set(["other", "No_ramp"]):
            state.iat[i, 6] = "other"
            state.iat[i, 7] = "F"
        #ランプなし
        elif set(unique) == set(["No_ramp"]):
            state.iat[i, 6] = "off"
            state.iat[i, 7] = "-"

        else:
            state.iat[i, 6] = "multi_color"
            state.iat[i, 7] = "-"
    """
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

