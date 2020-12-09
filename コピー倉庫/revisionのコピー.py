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

# normal_states ... ["ruck_num", "which_side", "shoot_position", "time_log", "group_num", "lamp_num", "num_of_lamps", "x", "y", "color", "LF"]
# additional ... ["movie", "x_num", "y_num"]
# delete ... ["movie", "group_num", "ramp_num"]
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


    # additional.csvを読み込み
    additional = pd.read_csv("additional.csv")
    # delete.csvを読み込み
    delete = pd.read_csv("delete.csv")
    # normal_states.csvを読み込み
    normal_states = pd.read_csv("normal_states.csv", index_col=0)
    # normal_state.csvに additionalカラム / deleteカラム　をそれぞれ用意
    normal_states["additional"] = None
    normal_states["distance"] = None
    # additionalの各レコードを読み込み、x_num / y_num　に相当する箇所にランプを挿入. additionalカラムにtrueをいれる.（この時点ではグループ見所属の欄外）
    y_step=20 #高さ方向のグリッド間隔(単位はピクセル)
    x_step=20 #幅方向のグリッド間隔(単位はピクセル)


    new_normal_states = pd.DataFrame([[0,0,0,0,0,0,0,0,0,0,0,0,0,0]], columns=[
        "ruck_num", 
        "which_side", 
        "shoot_position", 
        "time_log", 
        "group_num",
        "num_of_groups",
        "lamp_num", 
        "num_of_lamps", 
        "x", 
        "y", 
        "color",
        "LF",
        "additional",
        "distance"
    ])

    delete_process = pd.DataFrame([[0,0,0]], columns=[
        "movie", "del_x", "del_y"
    ])

    #基準
    ref_ruck_num = "a"
    ref_which_side = "a"
    ref_shoot_position = 0
    ref_group_num = 0
    #基準と比べてmovie_info+group_numが一致しない→新しいパートなので取得
    for i, each in enumerate(normal_states.itertuples()):
        ruck_num = each.ruck_num
        which_side = each.which_side
        shoot_position = each.shoot_position
        group_num = each.group_num
        if (str(ruck_num) == str(ref_ruck_num)) & (str(which_side) == str(ref_which_side)) & (str(shoot_position) == str(ref_shoot_position)) & (str(group_num) == str(ref_group_num)):
            pass  #各情報が基準と一致している場合、一つ前の要素と同じグループ内なのでパス
        else:
            part_normal_states = normal_states[  #各情報が基準と一致していない場合、一つ前までの要素とは異なるグループに入ったので、そのグループを部分として抜き出す
                (normal_states["ruck_num"]==ruck_num) & 
                (normal_states["which_side"]==which_side) & 
                (normal_states["shoot_position"]==shoot_position) &
                (normal_states["group_num"]==group_num)
                ]
            #print(part_normal_states)

            print("--------------------", i)
            for j, add_each in enumerate(additional.itertuples()):  #additionalを一つずつ回す
                #print(i)
                add_movie = add_each.movie
                add_ruck_num, add_which_side, add_shoot_position, add_time_log, _ = add_movie.replace(".mp4", "").split("_")
                add_group_num = each.group_num
                if np.array([
                    (str(add_ruck_num) == str(ruck_num)), 
                    (str(add_which_side) == str(which_side)), 
                    (str(add_shoot_position) == str(shoot_position)), 
                    (str(add_group_num) == str(group_num))
                    ]).all():
                    # x_num,y_numからそのセルの中心点(x, y)を計算する
                    x = add_each.x_num * x_step + (x_step/2)
                    y = add_each.y_num * y_step + (y_step/2)

                    add = {
                        "ruck_num":add_ruck_num, 
                        "which_side":add_which_side, 
                        "shoot_position":add_shoot_position, 
                        "time_log":add_time_log, 
                        "group_num":add_group_num, 
                        "lamp_num":None, 
                        "num_of_lamps":None, 
                        "x":int(x), 
                        "y":int(y), 
                        "color":None,
                        "LF": None,
                        "additional":1,
                        "distance":None
                        }
                    part_normal_states = part_normal_states.append(add, ignore_index=True)
                    print("add----------------------", j)
                else:
                    pass
                
            for j, each in enumerate(delete.itertuples()):  #deleteを一つずつ回す
                movie = each.movie
                del_ruck_num, del_which_side, delshoot_position, _, _ = movie.replace(".mp4", "").split("_")
                del_group_num = each.group_num
                del_lamp_num = each.lamp_num
                if np.array([
                    (str(del_ruck_num) == str(ruck_num)), 
                    (str(del_which_side) == str(which_side)), 
                    (str(delshoot_position) == str(shoot_position)), 
                    (str(del_group_num) == str(group_num))
                    ]).all():

                    del_x = part_normal_states.iat[del_lamp_num, 8]  # (del_lamp_num行, x)
                    del_y = part_normal_states.iat[del_lamp_num, 9]  # (del_lamp_num行, y)
                    delete_process = delete_process.append({"movie":movie, "del_x":del_x, "del_y":del_y}, ignore_index=True)
                else:
                    pass

            if (part_normal_states["additional"].sum() > 0):  #もしpart_normal_statesの中のadditionalの合計が1以上なら
                # movie情報から必要なmovieをチョイス
                for i, movie in enumerate(files_list):
                    _ruck_num, _which_side, _shoot_position, _, _ = movie.replace(".mp4", "").split("_")
                    if (_ruck_num==ruck_num) & (_which_side==which_side) & (int(_shoot_position)==int(shoot_position)):
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
                            
                            #mask_infoの作成-----------------------------------------------
                            #mask_info: ["ruck_num", "which_side", "shoot_position", "time_log", "x", "y", "group_num", "num_of_groups", "lamp_num", "num_of_lamps"]
                            stats_df =  part_normal_states.reindex(columns=["x", "y"]) # → stats_df...["x", "y"]

                            # delete_process分を削除する
                            #stats_dfとdelet_processを標準リストにすれば該当するところ消すとかできるのでは


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
                                    each.insert(2,str(i)) #グループナンバー
                                    each.insert(3,str(len(result_groups))) #グループ数
                                    each.insert(4,str(j)) #グループの中でのランプナンバー
                                    each.insert(5,str(len(group))) #ランプ数
                                    grouped_stats.append(each)

                            # 再度stats_dfとしてDF化
                            stats_df = pd.DataFrame(grouped_stats, columns=["x", "y", "group_num", "num_of_groups", "lamp_num", "num_of_lamps"])
                            
                            #マスク情報作成
                            #stats_dfをベースにmovie_infoをインサートしていく
                            stats_df.insert(0, "ruck_num", movie_info[0])  #df自体が更新されるので再代入不要
                            stats_df.insert(1, "which_side", movie_info[1] )
                            stats_df.insert(2, "shoot_position", movie_info[2]  )
                            stats_df.insert(3, "time_log", movie_info[3] )

                            mask_info = stats_df
                            #-----------------------------------------------

                            frames = module.cut_frame.cut_frame(cap, param)  # get_frameでフレームを取得
                            undistort_frames = module.undistort_frames.undistort_frames(frames, movie_info) #補正
                            lamp_imgs = module.get_lamp_imgs.get_lamp_imgs(mask_info, undistort_frames, param)
                            part_normal_states = module.get_lamp_state.get_lamp_state(lamp_imgs, mask_info, param)

                        print("---------------------------------------------")

            
            # part_normal_staesからdeleteのところだけ飛ばして

            # part_normal_statesをnew_normal_statesに追加
            new_normal_states = pd.concat([new_normal_states, part_normal_states])
            #基準値の入れ替え
            ref_ruck_num = ruck_num
            ref_which_side = which_side
            ref_shoot_position = shoot_position
            ref_group_num = group_num
    

    new_normal_states = new_normal_states.reset_index(drop = True)
    new_normal_states = new_normal_states.drop(index = 0)
    new_normal_states = new_normal_states.reset_index(drop = True)
    new_normal_states.to_csv("new_normal_states.csv")

    delete_process = delete_process.reset_index(drop = True)
    delete_process = delete_process.drop(index = 0)
    delete_process = delete_process.reset_index(drop = True)
    delete_process.to_csv("delete_process.csv")


    """
    # deleteの各レコードを読み込み、group_num, ranp_numに相当するランプのdeleteカラムにtrueをいれる.（この時点ではグループ見所属の欄外）
    # deleteカラムがfalseのもののみでグループ化を行う. r_group_num, r_num_of_groups, r_lamp_num, r_num_of_lamps として情報を記録
    # ランプ間距離を格納する「ditance」カラムを作成し、とりあえずxの相対距離を取得、格納
    # normal_state ... ["ruck_num", "which_side", "shoot_position", "time_log", "group_num", "num_of_groups", "lamp_num", "num_of_lamps", "x", "y", "color", "LF", "additional", "delete",  "r_group_num", "r_num_of_groups", "r_lamp_num", "r_num_of_lamps", "ditance"]
    # いらないカラムを切る
    # normal_state ... ["ruck_num", "which_side", "shoot_position", "time_log", "x", "y", "color", "LF", "additional", "delete",  "r_group_num", "r_num_of_groups", "r_lamp_num", "r_num_of_lamps", "ditance"]
    # カラムを並び替えて整理...normal_state ... ["ruck_num", "which_side", "shoot_position", "time_log", "r_group_num", "r_num_of_groups", "r_lamp_num", "r_num_of_lamps", "additional", "delete", "ditance", "x", "y", "color", "LF"]

    



    # 基準値の初期値
    # ref_ruck_num = str(normal_states[0:1]["ruck_num"])
    # ref_which_side = str(normal_states[0:1]["which_side"])
    # ref_shoot_position = int(normal_states[0:1]["shoot_position"])
    ref_ruck_num = "a"
    ref_which_side = "a"
    ref_shoot_position = 0
    # print("ref_ruck_num：", ref_ruck_num)
    # print("ref_which_side", ref_which_side)
    # print("ref_shoot_position", ref_shoot_position)

    y_step=20 #高さ方向のグリッド間隔(単位はピクセル)
    x_step=20 #幅方向のグリッド間隔(単位はピクセル)
    
    for i, row in enumerate(normal_states.itertuples()):
        if i == 0:   #refの初期化
            ref_ruck_num = row.ruck_num
            ref_which_side = row.which_side
            ref_shoot_position = row.shoot_position

        elif i == len(normal_states.index)-1: #最後の行での処理
            # 部分のdfを取ってくる処理
            part_normal_states = normal_states[
                (normal_states["ruck_num"]==ref_ruck_num) & 
                (normal_states["which_side"]==ref_which_side) & 
                (normal_states["shoot_position"]==ref_shoot_position)
                ]
            print("part_normal_states\n", part_normal_states)
            for j, each_add in enumerate(add.itertuples()):
                # eachの情報を ruck_num, which_side, shoot_position, x_num, y_num, color, FL に分けていれる
                ruck_num_add, which_side_add, shoot_position_add, time_log_add = each_add.movie.split("_")
                x_num = each_add.x_num
                y_num = each_add.y_num
                color = each_add.color
                LF = each_add.LF
                if (ruck_num_add == ref_ruck_num) & (which_side_add == ref_which_side) & (int(shoot_position_add) == ref_shoot_position):
                    # x_num,y_numからそのセルの中心点(x, y)を計算する
                    x = x_num * x_step + (x_step/2)
                    y = y_num * y_step + (y_step/2)
                    # その(x, y)をnormal_statesのmovie情報に該当する箇所の最初のindexに挿入する、どうせ下で整地されるのでlamp_numは0で統一、本indexがどうなるのかは作業しながら観察
                    part_normal_states = part_normal_states.append({"ruck_num":ruck_num_add, "which_side":which_side_add, "shoot_position":shoot_position_add, "time_log":time_log_add, "lamp_num":0, "x":x, "y":y, "color":color, "LF":LF}, ignore_index=True)
                    print("x = {}, y = {}".format(x, y))
                    print(part_normal_states)
                else:
                    pass
            # part_normal_statesをnew_normal_statesに追加
            new_normal_states = pd.concat([new_normal_states, part_normal_states])
            print("new_normal_states\n", new_normal_states)

        else:
            ruck_num = row.ruck_num
            which_side = row.which_side
            shoot_position = row.shoot_position

            if (ruck_num==ref_ruck_num) & (which_side==ref_which_side) & (shoot_position==ref_shoot_position):  #注目しているnormal_statesのある行と基準値refが同じ
                print(ref_ruck_num, ruck_num)
                print(ref_which_side, which_side)
                print(ref_shoot_position, shoot_position)
                pass  
            else:
                # 部分のdfを取ってくる処理
                part_normal_states = normal_states[(normal_states["ruck_num"]==ref_ruck_num) & (normal_states["which_side"]==ref_which_side) & (normal_states["shoot_position"]==ref_shoot_position)]
                print("part_normal_states\n", part_normal_states)

                for j, each_add in enumerate(add.itertuples()):
                    # eachの情報を ruck_num, which_side, shoot_position, x_num, y_num, color, FL に分けていれる
                    ruck_num_add, which_side_add, shoot_position_add, time_log_add = each_add.movie.split("_")
                    x_num = each_add.x_num
                    y_num = each_add.y_num
                    color = each_add.color
                    LF = each_add.LF
                    if (ruck_num_add == ref_ruck_num) & (which_side_add == ref_which_side) & (int(shoot_position_add) == ref_shoot_position):
                        # x_num,y_numからそのセルの中心点(x, y)を計算する
                        x = x_num * x_step + (x_step/2)
                        y = y_num * y_step + (y_step/2)
                        # その(x, y)をnormal_statesのmovie情報に該当する箇所の最初のindexに挿入する、どうせ下で整地されるのでlamp_numは0で統一、本indexがどうなるのかは作業しながら観察
                        part_normal_states = part_normal_states.append({"ruck_num":ruck_num_add, "which_side":which_side_add, "shoot_position":shoot_position_add, "time_log":time_log_add, "lamp_num":0, "x":x, "y":y, "color":color, "LF":LF}, ignore_index=True)
                        print("x = {}, y = {}".format(x, y))
                        print(part_normal_states)
                    else:
                        pass
                
                # part_normal_statesをnew_normal_statesに追加
                new_normal_states = pd.concat([new_normal_states, part_normal_states])
                print("new_normal_states\n", new_normal_states)

                # ref情報の更新
                ref_ruck_num = ruck_num
                ref_which_side = which_side
                ref_shoot_position = shoot_position
        
    new_normal_states = new_normal_states.reset_index(drop = True)
    new_normal_states = new_normal_states.drop(index = 0)
    new_normal_states = new_normal_states.reset_index(drop = True)

    # インデックスを振り直す
    #new_normal_states = new_normal_states.reset_index(drop = True)

    #print(normal_states)
    # normal_state.csvに再保存
    print(new_normal_states)
    new_normal_states.to_csv("normal_states.csv")
    """

if __name__ == "__main__":
    main()
