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
import openpyxl

import csv

import sklearn 
from sklearn.cluster import KMeans 

import module.cut_frame
import module.undistort_frames
import module.sum_frames
import module.get_mask_info

import module.get_lamp_imgs
import module.get_lamp_state

import json


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

    #現在時刻取得
    now = datetime.datetime.now()
    #resultファイル名フォーマット作成
    filename = 'result_log/result_' + now.strftime('%Y%m%d_%H%M%S') + '.csv'

    """
    #csvファイルの中身を空にする
    # with open('current_state.csv', 'w') as f:
    #     f.write('')
    with open('result.csv', 'w') as f:
        f.write('')
    """

    #当面の仕様では全動画はinputに入るので、まずは全てリスト取得
    path = "input/"
    files = os.listdir(path)
    files_list = [f for f in files if os.path.isfile(os.path.join(path, f))]
    files_list.remove('.DS_Store')
    print("ソート前：", files_list)

    #パラメータの読み込み
    json_open = open("param.json", "r")
    param = json.load(json_open)

    #動画ファイルのソート処理----------
    #ruckの並び順
    id_order = param["ruck_order"]

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
    #----------動画ファイルのソート処理

    """
    #マスク情報の読み込み（マスクcsvの構成とか今適当なのでこの辺どうインサート、読み込みしていくかも記述していく）
    with open("mask_info.csv") as f:
        reader = csv.reader(f)
        mask_infos = [row for row in reader]
    #正常状態情報の読み込み
    with open("normal_state.csv") as f:
        reader = csv.reader(f)
        normal_states = [row for row in reader]
    # #csvから戻すと数値がstrになるのでintに戻す
    # for i, each in enumerate(normal_state):
    #     normal_state[i][4] = int(each[4])
    """

    #正常状態csvのDataFrameでの読み込み
    normal_states = pd.read_csv("normal_states.csv", index_col=0)
    # get_lamp_imgs, get_lamp_state を make_mask_and_nomaly.py と共有するために引数normal_stateの形を整える（つまりmask_infoにする）
    mask_infos = normal_states.drop(columns=["color", "LF", "lamp_num"])
    
    #グローバルリスト（ここに諸情報を追加していき、最終的なアウトプットとする）
    current_states = pd.DataFrame([[0,0,0,0,0,0,0,0,0,0,0]], columns=[
        "ruck_num", 
        "which_side", 
        "shoot_position", 
        "time_log", 
        "lamp_num",
        "x", 
        "y", 
        "normal_color", 
        "normal_LF", 
        "current_color", 
        "current_LF"
        ])

    for i, movie in enumerate(files_list):
        print(i, "：", movie)
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

            #mask_infosからこの動画での対象となるmask_infoを取得
            mask_info = mask_infos.query('ruck_num == "{}" & which_side == "{}" & shoot_position == {}'.format(ruck_num, which_side, shoot_position))
            #mask_infosからこの動画での対象となるmask_infoを取得
            normal_state = normal_states.query('ruck_num == "{}" & which_side == "{}" & shoot_position == {}'.format(ruck_num, which_side, shoot_position))

            frames = module.cut_frame.cut_frame(cap, param) #フレームを切り出す
            undistort_frames = module.undistort_frames.undistort_frames(frames, movie_info) #補正
            lamp_imgs = module.get_lamp_imgs.get_lamp_imgs(mask_info, undistort_frames, param)
            current_state = module.get_lamp_state.get_lamp_state(lamp_imgs, mask_info, param)
            #print(current_state)

            #カラム名の変更
            normal_state = normal_state.rename(columns={'color': 'normal_color', 'LF': 'normal_LF'})
            current_state = current_state.rename(columns={'color': 'current_color', 'LF': 'current_LF'})
            #normal_state に current_state の current_color, current_LF をconcat（index）する
            normal_state = normal_state.assign(current_color = current_state["current_color"])
            normal_state = normal_state.assign(current_LF = current_state["current_LF"])

            #ループ外の current_states に追加していく
            current_states = pd.concat([current_states, normal_state], axis=0) 
            #current_states = ["ruck_num", "which_side", "shoot_position", "time_log", "lamp_num", "x", "y", "normal_color", "normal_LF", "current_color", "current_LF"]
            #print(current_states)

            
            #gif画像生成---------------
            x_step = param["gif_grid_x"] #幅方向のグリッド間隔(単位はピクセル)
            y_step = param["gif_grid_y"] #高さ方向のグリッド間隔(単位はピクセル)

            for j, frame in enumerate(undistort_frames):
                img_y,img_x = frame.shape[:2]  #オブジェクトimgのshapeメソッドの1つ目の戻り値(画像の高さ)をimg_yに、2つ目の戻り値(画像の幅)をimg_xに
                frame[y_step:img_y:y_step, :, :] = (0, 0, 255)  #横線を引く... y_stepからimg_yの手前までy_stepおきに横線を引く (0, 0, 255)...青
                frame[:, x_step:img_x:x_step, :] = (0, 0, 255)  #縦線を引く... x_stepからimg_xの手前までx_stepおきに縦線を引く (0, 0, 255)
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
                        text = '{}:{}:{}'.format(str(row.Index), str(row.current_color)[0], str(row.current_LF)), 
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
            clip.write_gif('mask_gif_main/{}_{}_{}_{}.gif'.format(ruck_num, which_side, shoot_position, time_log))
            #---------------gif画像生成
            

    #current_statesの先頭の不要な行を削除し、再度indexを振り直す
    current_states = current_states.reset_index(drop = True)
    current_states = current_states.drop(index = 0)
    current_states = current_states.reset_index(drop = True)


    #異常判定処理
    current_states["result"] = "a"  #新しいカラム[result]を定義&文字列で初期化
    print(current_states)
    print(current_states.iat[i, 11])
    for i, row in enumerate(current_states.itertuples()):
        if row.normal_color == row.current_color and row.normal_LF == row.current_LF:
            # current_states[i:i+1]["result"] = "-"  #←なぜかこの書き方だと値を更新できない、ので.iatで指定する
            current_states.iat[i, 11] = "N"
        else:
            # current_states[i:i+1]["result"] = "error"
            current_states.iat[i, 11] = "Error"
    print(current_states)

    #csv出力
    current_states.to_csv(filename)


if __name__ == "__main__":
    main()