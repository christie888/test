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
    #当面の仕様では全動画はinputに入るので、まずは全てリスト取得
    path = "pre_input/"
    files = os.listdir(path)
    files_list = [f for f in files if os.path.isfile(os.path.join(path, f))]
    if '.DS_Store' in files_list:
        files_list.remove('.DS_Store')

    #パラメータの読み込み
    json_open = open("param.json", "r")
    param = json.load(json_open)

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
    print(files_list)
    #----------

    """
    #csvファイルの中身を空にする
    with open('mask_info.csv', 'w') as f:
        f.write('')
    with open('normal_state.csv', 'w') as f:
        f.write('')
    """


    #グローバルリスト
    # mask_infos = pd.DataFrame([[0,0,0,0,0,0]], columns=["ruck_num", "which_side", "shoot_position", "time_log", "x", "y"])
    # print(mask_infos)
    normal_states = pd.DataFrame([[0,0,0,0,0,0,0,0]], columns=[
        "ruck_num", 
        "which_side", 
        "shoot_position", 
        "time_log", 
        "x", 
        "y", 
        "color", 
        "LF"
        ])


    #各動画に対して処理--------------------
    for i, movie in enumerate(files_list):
        cap =  cv2.VideoCapture(path + movie)

        if cap.isOpened()==False:
            print("[{}]：read error.".format(movie))
        else:
            print("[{}]：read success.".format(movie))

            #動画名から各種情報を取得
            ruck_num, which_side, shoot_position, time_log, cam_num = movie.replace(".mp4", "").split("_")  #ラック番号, ラックの左右情報, 撮影位置番号, 撮影date
            movie_info = [ruck_num, which_side, shoot_position, time_log, cam_num]
            print("start_processing----------")
            print("・ruck_num：{}\n・which_side：{}\n・shoot_position：{}\n・time_log：{}".format(ruck_num, which_side, shoot_position, time_log))
            print("--------------------------")

            #make_mask-----
            frames = module.cut_frame.cut_frame(cap, param) #フレームを切り出す
            undistort_frames = module.undistort_frames.undistort_frames(frames, movie_info) #補正
            sum_img = module.sum_frames.sum_frames(undistort_frames, param) #集合画像
            cv2.imwrite("sum_imgs/{}_{}_{}.jpg".format(ruck_num, which_side, shoot_position), sum_img)
            mask_info = module.get_mask_info.get_mask_info(sum_img, movie_info, param)  #mask_info...["ruck_num", "which_side", "shoot_position", "time_log", "x", "y", "group_num"]
            print(mask_info)
            #-----
            #make_normal_state_info-----
            lamp_imgs = module.get_lamp_imgs.get_lamp_imgs(mask_info, undistort_frames, param)
            """
            for j, row in enumerate(lamp_imgs):
                for k, img in enumerate(row):
                    cv2.imwrite("lamp_imgs/{}_{}_{}_frame{}_lamp{}.jpg".format(ruck_num, which_side, shoot_position, j, k),img)
            """
            normal_state = module.get_lamp_state.get_lamp_state(lamp_imgs, mask_info, param)
            #-----

            #ループ外のnormal_statesに追加していく、最後にcsv出力
            normal_states = pd.concat([normal_states, normal_state], axis=0)  

            # #連結画像の作成-----
            # lamp_imgs = np.array(lamp_imgs) #ndarray化

            # def concat_tile(im_list_2d):
            #     return cv2.vconcat([cv2.hconcat(im_list_h) for im_list_h in im_list_2d])
            # lamp_img_tile = concat_tile(lamp_imgs[:, 1:])  #インデックスを除いてから連結
            # cv2.imwrite("mask_lamp_tile/{}_{}_{}_{}.jpg".format(ruck_num, which_side, shoot_position, time_log), lamp_img_tile)
            # #-----


            #gif画像生成---------------
            x_step = param["gif_grid_x"] #幅方向のグリッド間隔(単位はピクセル)
            y_step = param["gif_grid_y"] #高さ方向のグリッド間隔(単位はピクセル)

            for j, frame in enumerate(undistort_frames):
                img_y,img_x = frame.shape[:2]  #オブジェクトimgのshapeメソッドの1つ目の戻り値(画像の高さ)をimg_yに、2つ目の戻り値(画像の幅)をimg_xに
                frame[y_step:img_y:y_step, :, :] = (0, 0, 255)  #横線を引く... y_stepからimg_yの手前までy_stepおきに横線を引く
                frame[:, x_step:img_x:x_step, :] = (0, 0, 255)  #縦線を引く... x_stepからimg_xの手前までx_stepおきに縦線を引く
                # 見やすくするため5本に一本色を変える
                frame[y_step:img_y:y_step*5, :, :] = (255, 0, 0)
                frame[:, x_step:img_x:x_step*5, :] = (255, 0, 0)
                
                # 認識外の範囲を視覚化
                remove_frame_thick = param["get_mask_info"]["remove_frame_thick"]
                x1 = remove_frame_thick
                x2 = param["frame_w"] - remove_frame_thick
                y1 = remove_frame_thick
                y2 = param["frame_h"] - remove_frame_thick
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), thickness=2)
                
                
                img_side = param["get_lamp_imgs"]["img_side"]
                for row in normal_state.itertuples():
                    #ランプ情報をputText
                    cv2.putText(
                        img = frame, 
                        text = '{}:{}:{}'.format(str(row.lamp_num), str(row.color)[0], str(row.LF)), 
                        org = (int(row.x), int(row.y)), 
                        fontFace =  cv2.FONT_HERSHEY_PLAIN, 
                        fontScale = 1,
                        color = (255, 255, 255), 
                        thickness = 2,
                        lineType = cv2.LINE_AA
                        )
                    #ランプ毎にカバーしているマスク範囲をフレームで視覚化
                    x1 = int(row.x - (img_side/2))
                    x2 = int(row.x + (img_side/2))
                    y1 = int(row.y - (img_side/2))
                    y2 = int(row.y + (img_side/2))
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), thickness=1)

                #目盛り（縦方向）
                for i in range(int(1200/y_step)):
                    cv2.putText(
                        img = frame, 
                        text = str(i),
                        org = (int(0), int(y_step + y_step * i)),
                        fontFace =  cv2.FONT_HERSHEY_PLAIN, 
                        fontScale = 1,
                        color = (255, 255, 255), 
                        thickness = 1,
                        lineType = cv2.LINE_AA
                        )
                #目盛り（横方向）
                for i in range(int(1600/x_step)):
                    cv2.putText(
                        img = frame, 
                        text = str(i),
                        org = (int(x_step * i), int(y_step)),
                        fontFace =  cv2.FONT_HERSHEY_PLAIN, 
                        fontScale = 1,
                        color = (255, 255, 255), 
                        thickness = 1,
                        lineType = cv2.LINE_AA
                        )

                    undistort_frames[j] = frame

            undistort_frames = list(undistort_frames)  #gifにするのに標準リスト化
            clip = ImageSequenceClip(undistort_frames, fps=2)
            clip.write_gif('mask_gif/{}_{}_{}_{}.gif'.format(ruck_num, which_side, shoot_position, time_log))
            #---------------gif画像生成
            

            #各種情報（撮影日時、ラック番号、L/R、撮影ポイント）をnormal_stateリストにインサート
            # for j in range(len(normal_state)):
            #     normal_state[j] = np.insert(normal_state[j], 0, time_log)
            #     normal_state[j] = np.insert(normal_state[j], 1, ruck_num)
            #     normal_state[j] = np.insert(normal_state[j], 2, which_side)
            #     normal_state[j] = np.insert(normal_state[j], 3, shoot_position)
                #print(normal_state[j])

            
            # #csvのクリアと追記、うまくできないから応急処置
            # if i == 0:
            #     #正常状態記録をcsv出力
            #     with open("normal_state.csv", "w") as f:
            #         writer = csv.writer(f)
            #         writer.writerows(normal_state)
            # else:
            #     #正常状態記録をcsv出力
            #     with open("normal_state.csv", "a") as f:
            #         writer = csv.writer(f)
            #         writer.writerows(normal_state)
            


    #csv出力
    normal_states = normal_states.reindex(columns=["ruck_num", "which_side", "shoot_position", "time_log", "group_num", "lamp_num", "x", "y", "color", "LF"])
    normal_states = normal_states.reset_index(drop=True)  #reset_index()をすると元のインデックスは[index]と言う列で残る
    normal_states = normal_states.drop(index = 0)
    normal_states = normal_states.reset_index(drop=True)
    print(normal_states)
    normal_states.to_csv("normal_states.csv") #normal_statesのcsv出力



    #この後
    #１：色判定結果リストを作成、点滅状態結果リストを作成、それらの組み合わせで状態リストを作成&csv出力する関数
    #現在、パスがめちゃくちゃなので修正
    #現在、一つの動画に対してしか判定していないので修正
    #

    #--------------------各動画に対して処理




if __name__ == "__main__":
    main()