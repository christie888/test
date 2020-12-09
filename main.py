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

import inspect

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

    # make_mask_and_normalと同じようにstateを取得（current_states）
    # その際r, degreeを取得
    # current_statesを動画単位、さらにグループ単位でブロック分けする（c-gブロック）
    # 同じグループブロックをnormal_statesから抜き出す（n-gブロック）
    
    # n-gブロックの0番目から範囲をとり、その中にc-gブロックの0番目が入っていれば、それを0番確定する. 入っていなければそのグループは終了.
    # c-gブロックのL01とdegree01が、n-gブロックのL01+-30, degree01+=10の範囲に入っていればそれを1番と確定する.
    # 入っていない場合、L01を確認.
    # n-gブロックのL01よりも短いのならそれはノイズであり、その先に1番ランプがあるはず。１番を削除してreset_index、再びL01とdegree01をとる
    # n-gブロックのL01よりも長いのなら、１番ランプは消灯エラーor認識漏れで拾えていない。c-g0番ランプとn-g０番ランプのズレを取得し、それをn-g１番ランプに適用したものをc-g１番ランプとし、カラーと点滅状態を取得する.
    # そこでランプが取得できたならそれをランプ情報とし、できなければ消灯エラーとする
    # これをc-gの最後で繰り返し、終わったら次のc-gに移る
    #　最終的にc-gのランプが全て特定されるはずなので、カラーと点滅情報の比較でresultを出す



    #現在時刻取得
    now = datetime.datetime.now()
    #resultファイル名フォーマット作成
    filename = 'result_log/result_' + now.strftime('%Y%m%d_%H%M%S') + '.csv'



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




    #正常状態csvのDataFrameでの読み込み
    normal_states = pd.read_csv("new_normal_states.csv", index_col=0)
    # --normal_states----------------------------------------
    # ruck_num	which_side, shoot_position, time_log, 
    # group_num	num_of_groups, lamp_num, num_of_lamps, x, y, 
    # color, LF, r, degree
    #--------------------------------------------------------
    # # get_lamp_imgs, get_lamp_state を make_mask_and_nomaly.py と共有するために引数normal_stateの形を整える（つまりmask_infoにする）
    # mask_infos = normal_states.drop(columns=["color", "LF", "lamp_num"])
    


    #グローバルリスト（ここに諸情報を追加していき、最終的なアウトプットとする）
    current_states = pd.DataFrame([[0,0,0,0,0,0,0,0,0,0,0,0,0,0]], columns=[
        "ruck_num", "which_side", "shoot_position", "time_log",
        "group_num", "num_of_groups", "lamp_num", "num_of_lamps", "x", "y", 
        "normal_color", "normal_LF", 
        "current_color", "current_LF"
        ])



    for i, movie in enumerate(files_list):
        print(i, "：", movie)
        cap =  cv2.VideoCapture(path + movie)

        if cap.isOpened()==False:
            print("[{}]：read error.".format(movie))
        else:
            print("[{}]：read success.".format(movie))


            # ------------------------------------------------------------------------------------------------------------------------

            # まずcurrentのこのmovieの
            # ------------------------------------------------------
            # ruck_num	which_side, shoot_position, time_log, 
            # group_num	num_of_groups, lamp_num, num_of_lamps, x, y
            # ------------------------------------------------------
            # だけ欲しいので make_mask_andnormal 同様の処理を行う

            #動画名から各種情報を取得
            ruck_num, which_side, shoot_position, time_log, cam_num = movie.replace(".mp4", "").split("_")  #ラック番号, ラックの左右情報, 撮影位置番号, 撮影date
            movie_info = [ruck_num, which_side, shoot_position, time_log, cam_num]
            print("start_processing----------")
            print("・ruck_num：{}\n・which_side：{}\n・shoot_position：{}\n・time_log：{}".format(ruck_num, which_side, shoot_position, time_log))
            print("--------------------------")

            frames = module.cut_frame.cut_frame(cap, param) #フレームを切り出す
            undistort_frames = module.undistort_frames.undistort_frames(frames, movie_info) #歪曲補正
            sum_img = module.sum_frames.sum_frames(undistort_frames, param) #集合画像作成
            cur_obj_info = module.get_mask_info.get_mask_info(sum_img, movie_info, param)
            cur_obj_info = cur_obj_info.reindex(columns=[
                "ruck_num", "which_side", "shoot_position", "time_log", 
                "group_num", "num_of_groups", "lamp_num", "num_of_lamps", "x", "y"
                ])
            # --cur_obj_info-----------------------------------------
            # ruck_num, which_side, shoot_position, time_log,
            # group_num, num_of_groups, lamp_num, num_of_lamps, x, y
            # -------------------------------------------------------

            # ------------------------------------------------------------------------------------------------------------------------
            # ------------------------------------------------------------------------------------------------------------------------

            # normal_states からこの動画での対象となる part_movie_ns を取得
            part_movie_ns = normal_states.query('ruck_num == "{}" & which_side == "{}" & shoot_position == {}'.format(ruck_num, which_side, shoot_position))
            # --part_movie_ns------------------------------------------
            # ruck_num, which_side, shoot_position, time_log, 
            # group_num, num_of_groups, lamp_num, num_of_lamps, x, y, 
            # color, LF, r, degree
            # ---------------------------------------------------------

            # cur_obj_info["num_of_groups"] と part_movie_ns["num_of_groups"] の一致
            if int(cur_obj_info.iat[0,5]) != int(part_movie_ns.iat[0,5]):
                print("--------------------------------------------------------------------------------")
                print("参照情報のグループ数：", part_movie_ns.iat[0,5])
                print("取得情報のグループ数：", cur_obj_info.iat[0,5])
                print("この撮影ポイントでのグループ数が一致しません. この撮影ポイントの検知をスキップします.")
                print("--------------------------------------------------------------------------------")
                # part_movie_ns に resultカラム をあとで追加するので、ここでは result に「num_of_groups Error」といれる.
            else:
                print("--------------------------------------------------------------------------------")
                print("参照情報のグループ数：", part_movie_ns.iat[0,5])
                print("取得情報のグループ数：", cur_obj_info.iat[0,5])
                print("グループ数の一致を確認. グループごとの処理に移行します.")
                print("--------------------------------------------------------------------------------")
                for i in range(int(cur_obj_info.iat[0,5])):
                    # cur_obj_info, part_movie_nsのそれぞれグループごとに切り分ける
                    cur_obj_info_group = cur_obj_info.query('group_num == {}'.format(i))
                    part_group_ns = part_movie_ns.query('group_num == {}'.format(i))
                    # DFだと操作が難しそうなので一度リストに戻す...
                    cur_obj_info_group = cur_obj_info_group.values.tolist()
                    part_group_ns = part_group_ns.values.tolist()
                    print("cur_obj_info_group:\n", cur_obj_info_group)
                    print("part_group_ns:\n", part_group_ns)
                    # 0番オブジェクトの特定
                    zero_x = part_group_ns[0][8]
                    zero_y = part_group_ns[0][9]
                    side =  100 # 範囲とする正方形の一辺
                    tmp = side/2
                    for i, each in enumerate(cur_obj_info):
                        obj_x = cur_obj_info_group[i][8]
                        obj_y = cur_obj_info_group[i][9]
                        if (obj_x >= zero_x - tmp) & (obj_x <= zero_x + tmp) & (obj_y >= zero_y - tmp) & (obj_y <= zero_y + tmp):
                            # i番オブジェクトを0番ランプに確定する。
                            # ０番ランプより前のレコードを cur_obj_info から削除する.
                            if i > 0:
                                del cur_obj_info_group[0:i]
                            break
                        # もし該当するものが最後まで現れなかったとき、このグループの０番は認識されていなかった. このグループの処理をスキップする.
                        if i == len(cur_obj_info_group)-1 :
                            print("--------------------------------------------------------------------------------")
                            print("０番ランプが何らかの要因でキャッチできていません. このグループの処理をスキップします")
                            print("--------------------------------------------------------------------------------")
                            #グループの処理を中断して次のグループに移るようにコードを書く
                    #print("cur_obj_info:\n", cur_obj_info_group)

                    
                    
                        


            # ------------------------------------------------------------------------------------------------------------------------

                
                
                

                




                        

if __name__ == "__main__":
    main()