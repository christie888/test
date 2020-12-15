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

import module.get_lamp_imgs
import module.get_lamp_state

import module.make_gif

import inspect
import json

import math

import operator



# additional ... ["movie", "x_num", "y_num"]
# delete ...     ["movie", "group_num", "ramp_num"]
def main():
    #パラメータの読み込み
    json_open = open("param.json", "r")
    param = json.load(json_open)

    #動画ファイル処理--------------------------------------------------
    path = "pre_input/"
    files = os.listdir(path)
    files_list = [f for f in files if os.path.isfile(os.path.join(path, f))]
    if '.DS_Store' in files_list:
        files_list.remove('.DS_Store')
    print("ソート前：", files_list)

    #ソート
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
    #--------------------------------------------------------------動画ファイル処理（終）


    # additional.csvを読み込み
    additional = pd.read_csv("additional.csv")
    # delete.csvを読み込み
    delete = pd.read_csv("delete.csv")
    
    # normal_states.csvを読み込み
    normal_states = pd.read_csv("normal_states.csv", index_col=0)
    # --normal_states----------------------------------------
    # ruck_num	which_side, shoot_position, time_log, 
    # group_num	num_of_groups, lamp_num, num_of_lamps, x, y, 
    # color, LF
    #--------------------------------------------------------

    # "num_of_lamps", color, LF は再定義するので除く. "num_of_groups","group_num", "lamp_num" はdeleteの対象をサーチする時に必要なので残す
    normal_states = normal_states.reindex(columns=[
        "ruck_num", "which_side", "shoot_position", "time_log", 
        "group_num", "num_of_groups", "lamp_num", "x", "y"
        ])
    # --normal_states---------------------------------
    # ruck_num	which_side, shoot_position, time_log, 
    # group_num, num_of_groups,lamp_num, x, y
    #-------------------------------------------------


    
    

    
    #２点間を曲座標ベクトル変換
    def getxy_RD(x, y, X, Y):
        _x, _y = (X-x), (Y-y)
        r = math.sqrt(_x**2+_y**2)
        rad = math.atan2(_y, _x)
        degree = math.degrees(rad)
        #print(r, degree)
        return r, degree


    # rev_part_ns_movie を順次追加していくDF
    new_normal_states = pd.DataFrame([[0,0,0,0,0,0,0,0,0,0,0,0,0,0]], columns=[
        "ruck_num", "which_side", "shoot_position", "time_log", 
        "group_num", "num_of_groups", "lamp_num", "num_of_lamps", "x", "y",
        "r", "degree", "color", "LF"
        ])

    # movie毎に分割
    for i, movie in enumerate(files_list):
        print(i, "：", movie)
        cap =  cv2.VideoCapture(path + movie)

        if cap.isOpened()==False:
            print("[{}]：read error.".format(movie))
        else:
            print("[{}]：read success.".format(movie))

            # 動画名から各種情報を取得
            ruck_num, which_side, shoot_position, time_log, cam_num = movie.replace(".mp4", "").split("_")  #ラック番号, ラックの左右情報, 撮影位置番号, 撮影date
            movie_info = [ruck_num, which_side, shoot_position, time_log, cam_num]
            print("start_processing----------")
            print("・ruck_num：{}\n・which_side：{}\n・shoot_position：{}\n・time_log：{}".format(ruck_num, which_side, shoot_position, time_log))
            print("--------------------------")

            # additional, delete を修正した part_ns_group を順次追加していくDF
            rev_part_ns_movie = pd.DataFrame([[0,0,0,0,0,0,0,0,0]], columns=[
                "ruck_num", "which_side", "shoot_position", "time_log", 
                "group_num","num_of_groups","lamp_num", "x", "y"
                ])


            # normal_states を movie毎に分割
            part_ns_movie = normal_states.query('ruck_num == "{}" & which_side == "{}" & shoot_position == {}'.format(ruck_num, which_side, shoot_position))
            # --part_ns_movie---------------------------------
            # ruck_num	which_side, shoot_position, time_log, 
            # group_num, num_of_groups, lamp_num, x, y
            #-------------------------------------------------



            # additional
            y_step = param["gif_grid_x"] #高さ方向のグリッド間隔(単位はピクセル)
            x_step = param["gif_grid_y"] #幅方向のグリッド間隔(単位はピクセル)
            for j, add_each in enumerate(additional.itertuples()):
                #print("additional:\n",j, "\n",  additional)
                add_ruck_num, add_which_side, add_shoot_position, add_time_log, _ = add_each.movie.replace(".mp4", "").split("_")
                if np.array([
                    (str(add_ruck_num) == str(ruck_num)), 
                    (str(add_which_side) == str(which_side)), 
                    (int(add_shoot_position) == int(shoot_position))
                    ]).all():
                    # x_num,y_numからそのセルの中心点(x, y)を計算する
                    add_x = add_each.x_num * x_step + (x_step/2)
                    add_y = add_each.y_num * y_step + (y_step/2)
                    add = [
                        add_ruck_num, #"ruck_num": 
                        add_which_side, #"which_side":
                        add_shoot_position, #"shoot_position":
                        add_time_log, #"time_log":
                        0, #"group_num":
                        part_ns_movie.iat[0,5], #"num_of_groups":
                        10000, #"lamp_num":
                        add_x, #"x":
                        add_y, #"y":
                    ]
                    #part_movie_T = part_movie.T
                    #part_movie_T.insert(0, j, add)
                    #part_movie = part_movie_T.T
                    #part_movie = part_movie.append(add, ignore_index=True)
                    part_ns_movie.loc[j+10000] = add   #適当なインデックスに追加（あとで整地されるからここでは追加さえできれば良い）
                    print("{}_part_ns_movie\n".format(j), part_ns_movie)
                    additional = additional.drop(0, errors='ignore')  #適用したらadditionalDFから削除
                    additional = additional.reset_index(drop = True)  # インデックス0が消えて先頭が1のままだと次回0を削除できないからインデックスを振り直す
                    print("{}_additional".format(j), additional)
                    print("additional...")
                    print("・ruck_num：{}\n・which_side：{}\n・shoot_position：{}\n・x：{}\n・y：{}\nを追加".format(ruck_num, which_side, shoot_position, x, y))



            # part_ns_movie を group毎に分割
            for j in range(int(part_ns_movie.iat[0, 5])):  #適当数繰り返す
                part_ns_group = part_ns_movie.query('group_num == {}'.format(j))
                # --part_ns_group---------------------------------
                # ruck_num	which_side, shoot_position, time_log, 
                # group_num, num_of_groups, lamp_num, x, y
                # -------------------------------------------------

                # # DFだと操作が難しそうなので一度リストに戻す...
                # part_ns_group = part_ns_group.values.tolist()
                # print("part_ns_group:\n", part_ns_group)
                #delete
                for k, del_each in enumerate(delete.itertuples()):
                    #print("delete:\n",j, "\n",  delete)
                    del_ruck_num, del_which_side, del_shoot_position, _, _ = del_each.movie.replace(".mp4", "").split("_")
                    if np.array([
                        (str(del_ruck_num) == str(ruck_num)), 
                        (str(del_which_side) == str(which_side)), 
                        (int(del_shoot_position) == int(shoot_position)),
                        (int(del_each.group_num) == int(part_ns_group.iat[0,4]))
                        ]).all():
                        # movie情報 & group_num & lamp_num が一致しないものだけ取得して再代入
                        part_ns_group = part_ns_group[part_ns_group["lamp_num"] != del_each.lamp_num]
                        delete = delete.drop(0, errors='ignore')  #適用したらdeleteDFから削除
                        delete = delete.reset_index(drop = True)
                        print("delete...")
                        print("・ruck_num：{}\n・which_side：{}\n・shoot_position：{}\n・group_num：{}\n・lamp_num：{}\nを削除".format(ruck_num, which_side, shoot_position, del_each.group_num, del_each.lamp_num))
                        if part_ns_group.empty:
                            break

                # part_ns_group を rev_part_ns_movie にconcat
                rev_part_ns_movie = pd.concat([rev_part_ns_movie, part_ns_group])
                # --rev_part_ns_movie-----------------------------
                # ruck_num, which_side, shoot_position, time_log, 
                # group_num, num_of_groups, lamp_num, x, y
                #-------------------------------------------------

            # rev_part_ns_movie を rev_ns にconcat
            rev_part_ns_movie = rev_part_ns_movie.reset_index(drop = True)
            rev_part_ns_movie = rev_part_ns_movie.drop(index = 0)
            rev_part_ns_movie = rev_part_ns_movie.reset_index(drop = True)




            #グルーピング & 極座標
            def isInThreshold(value, group_min_y, threshold):
                return (value >= group_min_y) and (value < group_min_y + threshold)
            
            _rev_part_ns_movie = rev_part_ns_movie.copy()
            _rev_part_ns_movie = _rev_part_ns_movie.values.tolist()  #一度リストに変換
            # make_mask_and_normal の時点で整地されており、このままではグルーピングのルールが異なるため、一度 _rev_part_ns_movie の　"y" で再びソートする
            _rev_part_ns_movie = sorted(_rev_part_ns_movie, key=operator.itemgetter(8))  #8..."y"

            tmp = None
            threshold = param["get_mask_info"]["group_y_range"]  #閾値 px

            result_groups = []  #３次元配列 [group0(2次元), group1, group2, ...] 
            while True:
                if len(_rev_part_ns_movie) == 0:
                    break
                tmp = _rev_part_ns_movie.pop(0) #pop...指定した値の要素を取得し、元のリストから削除する
                y = tmp[8]
                group = [tmp]
                for _tmp in _rev_part_ns_movie[:]:
                    if isInThreshold(int(_tmp[8]), int(y), int(threshold)):
                        group.append(_tmp)
                        _rev_part_ns_movie.remove(_tmp)
                group = sorted(group, key=operator.itemgetter(7))  # result_groupsを要素ごとに x でソート
                result_groups.append(group)
            #print(result_groups)

            grouped_stats = []  #３次元リストから再び２次元リストに戻す. その際所属グループのナンバーとランプナンバーを要素に入れこむ.
            for k, group in enumerate(result_groups):
                for l, each in enumerate(group):
                    each[4] = k  #group_num
                    each[5] = len(result_groups)  #num_of_groups（人グループを）
                    each[6] = l  #lamp_num
                    each.insert(7, len(group))  #num_of_groups

                    # 極座標ベクトル
                    if l == len(group) - 1:
                        each.insert(10, 0)  #r
                        each.insert(11, 0)  #degree
                    else:
                        x = group[l][8]
                        y = group[l][9]
                        X = group[l+1][7]
                        Y = group[l+1][8]
                        r, degree = getxy_RD(x, y, X, Y)
                        each.insert(10,str(r))
                        each.insert(11,str(degree))

                    grouped_stats.append(each)

            #--grouped_stats-----------------------------------------
            # ruck_num, which_side, shoot_position, time_log, 
            # group_num, num_of_groups, lamp_num, num_of_lamps,  x, y,
            # r, degree
            #---------------------------------------------------------

            # grouped_stats を再びDF化
            rev_part_ns_movie = pd.DataFrame(grouped_stats, columns=[
                "ruck_num", "which_side", "shoot_position", "time_log", 
                "group_num", "num_of_groups", "lamp_num", "num_of_lamps",  "x", "y",
                "r", "degree"
            ])


            #ランプの状態検知
            frames = module.cut_frame.cut_frame(cap, param) #フレームを切り出す
            undistort_frames = module.undistort_frames.undistort_frames(frames, movie_info) #補正
            #sum_img = module.sum_frames.sum_frames(undistort_frames, param) #集合画像

            # mask_info----------------------------------------------
            # ruck_num, which_side, shoot_position, time_log,
            # group_num, num_of_groups, lamp_num, num_of_lamps, x, y
            # -------------------------------------------------------
            mask_info = rev_part_ns_movie.reindex(columns=[
                "ruck_num", "which_side", "shoot_position", "time_log", 
                "group_num", "num_of_groups", "lamp_num", "num_of_lamps", "x", "y"
                ])
            lamp_imgs = module.get_lamp_imgs.get_lamp_imgs(mask_info, undistort_frames, param)  #ランプ画像
            rev_ns = module.get_lamp_state.get_lamp_state(lamp_imgs, mask_info, param)  #状態

            #gif画像生成
            module.make_gif.make_gif(undistort_frames, rev_ns, movie_info, param, "mask_gif_rev")

            # rev_part_ns_movie と rev_ns をいい感じにconcatして
            # new_normal_state --------------------------------------
            # ruck_num, which_side, shoot_position, time_log,
            # group_num, num_of_groups, lamp_num, num_of_lamps, x, y,
            # "r", "degree", "color", "LF"
            # -------------------------------------------------------
            # に整える.
            rev_ns = rev_ns.reindex(columns=["color", "LF"])
            new_normal_state = pd.concat([rev_part_ns_movie, rev_ns], axis=1)
            
            # rev_part_ns_movie を rev_ns にconcat
            new_normal_states = pd.concat([new_normal_states, new_normal_state], axis=0)
            
            
    new_normal_states = new_normal_states.reset_index(drop = True)
    new_normal_states = new_normal_states.drop(index = 0)
    new_normal_states = new_normal_states.reset_index(drop = True)
    new_normal_states.to_csv("new_normal_states.csv") 


if __name__ == "__main__":
    main()
