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

import module.cut_frame
import module.undistort_frames
import module.sum_frames
import module.get_mask_info

import module.get_ramp_imgs
import module.get_ramp_state


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
    #動画ファイル格納　なんかうまく繰り返し構文で書けなかった
    # for path in [fujitsu_L_path,fujitsu_R_path,dell_L_path,dell_R_path]:
    #     files = os.listdir(path)
    #     fujitsu_L_files = [f for f in files if os.path.isfile(os.path.join(path, f))]
    #     print(fujitsu_L_files)
    #応急処置-----
    # files = os.listdir(fujitsu_L_path)
    # files_list[0] = [f for f in files if os.path.isfile(os.path.join(fujitsu_L_path, f))]

    # files = os.listdir(fujitsu_R_path)
    # files_list[1] = [f for f in files if os.path.isfile(os.path.join(fujitsu_R_path, f))]

    # files = os.listdir(dell_L_path)
    # files_list[2] = [f for f in files if os.path.isfile(os.path.join(dell_L_path, f))]

    # files = os.listdir(dell_R_path)
    # files_list[3] = [f for f in files if os.path.isfile(os.path.join(dell_R_path, f))]

    # print(files_list[0])
    # print(files_list[1])
    # print(files_list[2])
    # print(files_list[3])
    #-----

    #現在時刻取得&ファイル名フォーマット作成
    now = datetime.datetime.now()
    filename = 'result_log/result_' + now.strftime('%Y%m%d_%H%M%S') + '.csv'


    #csvファイルの中身を空にする
    with open('current_state.csv', 'w') as f:
        f.write('')
    with open('result.csv', 'w') as f:
        f.write('')


    #当面の仕様では全動画はinputに入るので、まずは全てリスト取得
    path = "input/"
    files = os.listdir(path)
    files_list = [f for f in files if os.path.isfile(os.path.join(path, f))]
    files_list.remove('.DS_Store')
    print(files_list)

    
    #動画ファイルのソート処理----------
    #ruckの並び順
    id_order = ["R06C08-A", "R06C08-B", "R06C08-C"]

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
        file1_id, file1_lr, file1_number, _ = file1.split("_")
        file2_id, file2_lr, file2_number, _ = file2.split("_")
        if file1_id != file2_id:
            return id_order.index(file1_id) - id_order.index(file2_id)
        if file1_lr != file2_lr:
            if file1_lr == "L":
                return -1
            return 1
        return int(file1_number) - int(file2_number)
    files_list.sort(key=cmp_to_key(compare_files))
    print(files_list)
    #----------

    
    #マスク情報の読み込み（マスクcsvの構成とか今適当なのでこの辺どうインサート、読み込みしていくかも記述していく）
    with open("mask_info.csv") as f:
        reader = csv.reader(f)
        mask_info = [row for row in reader]
    #正常状態情報の読み込み
    with open("normal_state.csv") as f:
        reader = csv.reader(f)
        normal_state = [row for row in reader]
    # #csvから戻すと数値がstrになるのでintに戻す
    # for i, each in enumerate(normal_state):
    #     normal_state[i][4] = int(each[4])



    for i, movie in enumerate(files_list):
        print(i, "：", movie)
        cap =  cv2.VideoCapture(path + movie)

        if cap.isOpened()==False:
            print("[{}]：読み込めませんでした".format(movie))
        else:
            print("[{}]：読み込み成功".format(movie))

            #動画名から各種情報を取得
            ruck_num, which_side, shoot_position, time_log = movie.replace(".mp4", "").split("_")  #ラック番号, ラックの左右情報, 撮影位置番号, 撮影date
            movie_info = [ruck_num, which_side, shoot_position, time_log]

            #モジュール利用
            frames = module.cut_frame.cut_frame(cap) #フレームを切り出す
            undistort_frames = module.undistort_frames.undistort_frames(frames) #補正
            ramp_imgs = module.get_ramp_imgs.get_ramp_imgs(mask_info, undistort_frames, movie_info)
            current_state = module.get_ramp_state.get_ramp_state(ramp_imgs, movie_info)


            #連結画像の作成-----
            ramp_imgs = np.array(ramp_imgs) #ndarray化

            def concat_tile(im_list_2d):
                return cv2.vconcat([cv2.hconcat(im_list_h) for im_list_h in im_list_2d])
            ramp_img_tile = concat_tile(ramp_imgs[:, 1:])  #インデックスを除いてから連結
            cv2.imwrite("current_ramp_tile/{}_{}_{}_{}.jpg".format(ruck_num, which_side, shoot_position, time_log), ramp_img_tile)
            #-----





            # #各種情報（撮影日時、ラック番号、L/R、撮影ポイント）をcerrent_stateリストにインサート
            # for j in range(len(current_state)):
            #     current_state[j] = np.insert(current_state[j], 0, time_log)
            #     current_state[j] = np.insert(current_state[j], 1, ruck_num)
            #     current_state[j] = np.insert(current_state[j], 2, which_side)
            #     current_state[j] = np.insert(current_state[j], 3, shoot_position)
            #     #print(current_state[j])

            # #csvのクリアと追記、うまくできないから応急処置
            # if i == 0:
            #     #正常状態記録をcsv出力
            #     with open("current_state.csv", "w") as f:
            #         writer = csv.writer(f)
            #         writer.writerows(current_state)
            # else:
            #     #正常状態記録をcsv出力
            #     with open("current_state.csv", "a") as f:
            #         writer = csv.writer(f)
            #         writer.writerows(current_state)
            

            # #比較→正常/異常判定
            # #currentとnormalをソートして上から順に照らし合わせる or currentの[0]-[4]に該当するnormalをサーチしてきて比較する
            # result = []
            # for k, (cur, nor) in enumerate(zip(current_state, normal_state)):
            #     if str(cur[5])==str(nor[5]) and str(cur[6])==str(nor[6]):
            #         result.append([cur[0], cur[1], cur[2], cur[3], cur[4], cur[5], cur[6],  True])
            #         #print(k, "：", cur, "/", nor, True)
            #     else:
            #         result.append([cur[0], cur[1], cur[2], cur[3], cur[4], cur[5], cur[6], False])
            #         #print(k, "：", cur, "/", nor, False)


            #比較→正常/異常判定 サーチ
            result = []
            for cur in current_state:
                for nor in normal_state:
                    if str(cur[0])==str(nor[0]) and str(cur[1])==str(nor[1]) and str(cur[2])==str(nor[2]) and str(cur[4])==str(nor[4]):
                        if str(cur[5])==str(nor[5]) and str(cur[6])==str(nor[6]):
                            result.append([cur[0], cur[1], cur[2], cur[3], cur[4], cur[5], cur[6], True])
                            break
                        else:
                            result.append([cur[0], cur[1], cur[2], cur[3], cur[4], cur[5], cur[6], False])
                            break
                    else:
                        pass
                else:
                    print("エラー：[{}]のランプについて正常状態が記録されていません.".format(cur))
                    result.append([cur[0], cur[1], cur[2], cur[3], cur[4], cur[5], cur[6], "?"])


            #正常/異常判定記録をcsv出力
            with open(filename, "a") as f:
                writer = csv.writer(f)
                writer.writerows(result)



if __name__ == "__main__":
    main()