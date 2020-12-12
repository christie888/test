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

import PIL   #PILのインストールはできない. その後継のpillowをインストールするとimportできるようになる
from PIL import Image
from moviepy.editor import ImageSequenceClip


from IPython.display import display


import pandas as pd
#エクセル操作
import openpyxl as xl
from openpyxl.styles import PatternFill  #セルの色変更


import csv

import sklearn 
from sklearn.cluster import KMeans 

import module.cut_frame
import module.undistort_frames
import module.sum_frames
import module.get_mask_info

import module.get_lamp_imgs
import module.get_lamp_state

import module.make_gif

import inspect

import json


#一つのサーバラックには片側10箇所の撮影ポイントがあるが、テスト用動画では片側5箇所となる
#１撮影ポイントに関する情報を得るコードを書き、それをコード内で繰り返していく
#もちろんcsvに更新するときは更新ではなくインサート
#おそらく一気に動画を読み込むよりも順番に読み込んだ方が効率良いので、毎回変数に読み込んで、動画データを更新する方針

#動画パス
# fujitsu_L_path = "input/fujitsu_rack/L/"
# fujitsu_R_path = "input/fujitsu_rack/R/"
# dell_L_path = "input/dell_rack/L/"
# dell_R_path = "input/dell_rack/R/"

#動画格納リスト
# fujitsu_L_files = []
# fujitsu_R_files = []
# dell_L_files = []
# dell_R_files = []
# files_list = [[],[],[],[]]



def main():
    #パラメータの読み込み
    json_open = open("param.json", "r")
    param = json.load(json_open)

    #当面の仕様では全動画はinputに入るので、まずは全てリスト取得
    path = "pre_input/"
    files = os.listdir(path)
    files_list = [f for f in files if os.path.isfile(os.path.join(path, f))]
    if '.DS_Store' in files_list:
        files_list.remove('.DS_Store')
    print("ソート前：", files_list)

    #動画ファイルのソート処理----------
    id_order = param["ruck_order"]  #ruckの並び順

    def cmp_to_key(mycmp):
        'Convert a cmp= function into a key= function'
        class K:
            def __init__(self, obj, *args):
                self.obj = obj
            def __lt__(self, other):
                return mycmp(self.obj, other.obj) < 0
            def __gt__(self, other):
                return mycmp(self.obj, other.obj) > 0
            def __eq__(self, other):
                return mycmp(self.obj, other.obj) == 0
            def __le__(self, other):
                return mycmp(self.obj, other.obj) <= 0
            def __ge__(self, other):
                return mycmp(self.obj, other.obj) >= 0
            def __ne__(self, other):
                return mycmp(self.obj, other.obj) != 0
        return K
    def compare_files(file1, file2):
        file1_id, file1_lr, file1_number, _, _ = file1.split("_")
        file2_id, file2_lr, file2_number, _, _ = file2.split("_")
        if file1_id != file2_id:
            return id_order.index(file1_id) - id_order.index(file2_id)
        if file1_lr != file2_lr:
            if file1_lr == "L":
                return -1
            return 1
        return int(file1_number) - int(file2_number)
    files_list.sort(key=cmp_to_key(compare_files))
    print("ソート後：", files_list)
    #----------


    #グローバルリスト
    # mask_infos = pd.DataFrame([[0,0,0,0,0,0]], columns=["ruck_num", "which_side", "shoot_position", "time_log", "x", "y"])
    # print(mask_infos)
    normal_states = pd.DataFrame([[0,0,0,0,0,0,0,0]], columns=[
        "ruck_num", "which_side", "shoot_position", "time_log", 
        "x", "y", 
        "color", "LF"
        ])


    #各動画に対して処理--------------------
    for i, movie in enumerate(files_list):
        cap =  cv2.VideoCapture(path + movie)

        if cap.isOpened()==False:
            print("[{}]：read error.".format(movie))
        else:
            print("[{}]：read success.".format(movie))

            #動画名から各種情報を取得
            ruck_num, which_side, shoot_position, time_log, cam_num = movie.replace(".mp4", "").split("_")  #ラック番号, ラックの左右情報, 撮影位置番号, 撮影date, カメラナンバー
            movie_info = [ruck_num, which_side, shoot_position, time_log, cam_num]
            print("start_processing----------")
            print("・ruck_num：{}\n・which_side：{}\n・shoot_position：{}\n・time_log：{}".format(ruck_num, which_side, shoot_position, time_log))
            print("--------------------------")

            # make_mask / make_normal_state_info----------
            #input-------------------------------------------------------------------------------------------------------------------------------------------------------------
            # mask_info：   ["ruck_num", "which_side", "shoot_position", time_log, "x", "y", "group_num", "num_of_groups", "lamp_num", "num_of_lamps"]
            # normal_state：["ruck_num", "which_side", "shoot_position", time_log, "x", "y", "group_num", "num_of_groups", "lamp_num", "num_of_lamps", color", "LF"]
            #------------------------------------------------------------------------------------------------------------------------------------------------------------------
            frames = module.cut_frame.cut_frame(cap, param) #フレームを切り出す
            undistort_frames = module.undistort_frames.undistort_frames(frames, movie_info) #補正
            sum_img = module.sum_frames.sum_frames(undistort_frames, param) #集合画像
            #cv2.imwrite("sum_imgs_main/{}_{}_{}.jpg".format(ruck_num, which_side, shoot_position), sum_img)
            mask_info = module.get_mask_info.get_mask_info(sum_img, movie_info, param)  #mask_info...["ruck_num", "which_side", "shoot_position", time_log, "x", "y", "group_num", "num_of_groups", "lamp_num", "num_of_lamps"]
            
            lamp_imgs = module.get_lamp_imgs.get_lamp_imgs(mask_info, undistort_frames, param)
            normal_state = module.get_lamp_state.get_lamp_state(lamp_imgs, mask_info, param)
            """
            # 一つ一つのランプ画像を保存
            for j, row in enumerate(lamp_imgs):
                for k, img in enumerate(row):
                    cv2.imwrite("lamp_imgs/{}_{}_{}_frame{}_lamp{}.jpg".format(ruck_num, which_side, shoot_position, j, k),img)
            """
            #---------------------------------------------

            #ループ外のnormal_statesに追加していく、最後にcsv出力
            normal_states = pd.concat([normal_states, normal_state], axis=0)

            #gif画像生成
            module.make_gif.make_gif(undistort_frames, normal_state, movie_info, param, "mask_gif")

            # #連結画像の作成-----
            # lamp_imgs = np.array(lamp_imgs) #ndarray化

            # def concat_tile(im_list_2d):
            #     return cv2.vconcat([cv2.hconcat(im_list_h) for im_list_h in im_list_2d])
            # lamp_img_tile = concat_tile(lamp_imgs[:, 1:])  #インデックスを除いてから連結
            # cv2.imwrite("mask_lamp_tile/{}_{}_{}_{}.jpg".format(ruck_num, which_side, shoot_position, time_log), lamp_img_tile)
            # #-----


    #csv出力
    normal_states = normal_states.reindex(columns=["ruck_num", "which_side", "shoot_position", "time_log", "group_num", "num_of_groups", "lamp_num", "num_of_lamps", "x", "y", "color", "LF"])
    normal_states = normal_states.reset_index(drop=True)
    normal_states = normal_states.drop(index = 0)
    normal_states = normal_states.reset_index(drop=True)
    print(normal_states)
    normal_states.to_csv("normal_states.csv") #normal_statesのcsv出力


    #--------------------各動画に対して処理




if __name__ == "__main__":
    main()