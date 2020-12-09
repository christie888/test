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


# normal_states ...     ["ruck_num", "which_side", "shoot_position", "time_log", "group_num", "lamp_num", "num_of_lamps", "x", "y", "color", "LF"]
# additional ...        ["movie", "x_num", "y_num"]
# delete ...            ["movie", "group_num", "ramp_num"]
# new_normal_states ... ["ruck_num", "which_side", "shoot_position", "time_log", "group_num", "lamp_num", "num_of_lamps", "x", "y", "r", "θ", "color", "LF"]
def main():

    #パラメータの読み込み
    json_open = open("param.json", "r")
    param = json.load(json_open)



    #動画ファイル処理--------------------------------------------------

    #当面の仕様では全動画はinputに入るので、まずは全てリスト取得
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
    #-----------------------------------------------------------------------


    # additional.csvを読み込み
    additional = pd.read_csv("additional.csv")
    # delete.csvを読み込み
    delete = pd.read_csv("delete.csv")
    # normal_states.csvを読み込み
    normal_states = pd.read_csv("normal_states.csv", index_col=0)
    #"num_of_groups","num_of_lamps"は再定義するので除く. "group_num", "lamp_num" はdeleteの対象をサーチする時に必要なので残す
    normal_states = normal_states.reindex(columns=["ruck_num", "which_side", "shoot_position", "time_log", "group_num","lamp_num", "x", "y"])
    
    # additionalの各レコードを読み込み、x_num / y_num　に相当する箇所にランプを挿入. 
    y_step=20 #高さ方向のグリッド間隔(単位はピクセル)
    x_step=20 #幅方向のグリッド間隔(単位はピクセル)

    # normal_statesと形を揃えた新しいdfを作る
    tmp_ns = pd.DataFrame([[0,0,0,0,0,0,0,0]], columns=[
        "ruck_num", 
        "which_side", 
        "shoot_position", 
        "time_log", 
        "group_num",
        #"num_of_groups",
        "lamp_num", 
        #"num_of_lamps", 
        "x", 
        "y"
    ])


    #２点間を曲座標ベクトル変換
    def getxy_RD(x, y, X, Y):
        _x, _y = (X-x), (Y-y)
        r = math.sqrt(_x**2+_y**2)
        rad = math.atan2(_y, _x)
        degree = math.degrees(rad)
        print(r, degree)
        return r, degree



    # 基準値初期化
    ref_ruck_num = "a"
    ref_which_side = "a"
    ref_shoot_position = 0
    ref_group_num = 0
    # 基準値と比べて movie_info & group_num が一致しない → 新しいパートなので取得
    for i, ns_each in enumerate(normal_states.itertuples()):
        if (
            (str(ns_each.ruck_num) == str(ref_ruck_num)) & 
            (str(ns_each.which_side) == str(ref_which_side)) & 
            (str(ns_each.shoot_position) == str(ref_shoot_position)) & 
            (str(ns_each.group_num) == str(ref_group_num))
            ):
            pass  #各情報が基準と一致している場合、一つ前の要素と同じグループ内なのでパス
        else:
            part_normal_states = normal_states[  #各情報が基準と一致していない場合、一つ前までの要素とは異なるグループに入ったので、そのグループを部分として抜き出す
                (normal_states["ruck_num"] == ns_each.ruck_num) & 
                (normal_states["which_side"] == ns_each.which_side) & 
                (normal_states["shoot_position"] == ns_each.shoot_position) &
                (normal_states["group_num"] == ns_each.group_num)
                ]
                
            #additionalを一つずつ回す
            for j, add_each in enumerate(additional.itertuples()):
                add_ruck_num, add_which_side, add_shoot_position, add_time_log, _ = add_each.movie.replace(".mp4", "").split("_")
                if np.array([
                    (str(add_ruck_num) == str(ns_each.ruck_num)), 
                    (str(add_which_side) == str(ns_each.which_side)), 
                    (str(add_shoot_position) == str(ns_each.shoot_position))
                    ]).all():
                    # x_num,y_numからそのセルの中心点(x, y)を計算する
                    x = add_each.x_num * x_step + (x_step/2)
                    y = add_each.y_num * y_step + (y_step/2)

                    add = {
                        "ruck_num":add_ruck_num, 
                        "which_side":add_which_side, 
                        "shoot_position":add_shoot_position, 
                        "time_log":add_time_log, 
                        "group_num":None, 
                        "lamp_num":None,
                        "x":int(x), 
                        "y":int(y)
                        }
                    part_normal_states = part_normal_states.append(add, ignore_index=True)
                    additional = additional.drop(j)  #適用したらadditionalDFから削除
                else:
                    pass

            #deleteを一つずつ回す
            for j, del_each in enumerate(delete.itertuples()):
                del_ruck_num, del_which_side, del_shoot_position, _, _ = del_each.movie.replace(".mp4", "").split("_")
                # del_each.movie, del_each.group_num, del_each.lamp_numが全て一致するレコードを除いて新たな part_normal_states とする.
                if np.array([
                    (str(del_ruck_num) == str(ns_each.ruck_num)), 
                    (str(del_which_side) == str(ns_each.which_side)), 
                    (str(del_shoot_position) == str(ns_each.shoot_position)),
                    (str(del_each.group_num) == str(ns_each.group_num))
                    ]).all():
                    part_normal_states = part_normal_states[part_normal_states["lamp_num"] != del_each.lamp_num]
                    delete = delete.drop(j)  #適用したらdeleteDFから削除
                else:
                    pass

            # part_normal_statesをnew_normal_statesに追加
            tmp_ns = pd.concat([tmp_ns, part_normal_states])
            #基準値の入れ替え
            ref_ruck_num = ns_each.ruck_num
            ref_which_side = ns_each.which_side
            ref_shoot_position = ns_each.shoot_position
            ref_group_num = ns_each.group_num


    tmp_ns = tmp_ns.reset_index(drop = True)
    tmp_ns = tmp_ns.drop(index = 0)
    tmp_ns = tmp_ns.reset_index(drop = True)
    tmp_ns = tmp_ns.reindex(columns=["ruck_num", "which_side", "shoot_position", "time_log", "x", "y"])
    print(tmp_ns)
    #-----------------------
    # ここまでで修正を施した
    # tmp_ns = ["ruck_num", "which_side", "shoot_position", "time_log", "x", "y"]
    # が完成
    #-----------------------


    # tmp_nsにグルーピングをかけて group_num, num_of_groups, lamp_num, num_of_groups 情報を追加する

    #グルーピング-----
    def isInThreshold(value, center, threshold):
        return (value < center + threshold) and (center - threshold < value)
    
    _tmp_ns = tmp_ns.copy()
    _tmp_ns = _tmp_ns.values.tolist()
    tmp = None
    threshold = 100  #閾値 px

    result_groups = []   #二次元配列 
    while True:
        if len(_tmp_ns) == 0:
            break
        tmp = _tmp_ns.pop(0) #pop...指定した値の要素を取得し、元のリストから削除する
        y = tmp[5]  # 要素番号1＝y
        print("y:",y)
        group = [tmp]
        for _tmp in _tmp_ns[:]:
            if isInThreshold(_tmp[5], y, threshold):
                group.append(_tmp)
                _tmp_ns.remove(_tmp)
        print(group)
        group = sorted(group)  # result_groupsを要素ごとにx（要素番号0）でソート
        result_groups.append(group)
    
    grouped_stats = []  #３次元リストから再び２次元リストに戻す. その際所属グループのナンバーとランプナンバーを要素に入れこむ.
    for k, group in enumerate(result_groups):
        for l, each in enumerate(group):
            each.insert(4,str(k))  #group_num
            each.insert(5,len(result_groups))  #num_of_groups（人グループを）
            each.insert(6,str(l))  #lamp_num
            each.insert(7,str(len(group)))  #num_of_groups
            grouped_stats.append(each)
    #-----グルーピング（終）

    print(grouped_stats)













            



    #         # movie情報から必要なmovieをチョイス
    #         for j, movie in enumerate(files_list):
    #             _ruck_num, _which_side, _shoot_position, _, _ = movie.replace(".mp4", "").split("_")
    #             if (_ruck_num == ns_each.ruck_num) & (_which_side == ns_each.which_side) & (int(_shoot_position) == int(ns_each.shoot_position)):
    #                 cap =  cv2.VideoCapture(path + movie)
    #                 if cap.isOpened()==False:
    #                     print("[{}]：read error.".format(movie))
    #                 else:
    #                     print("[{}]：read success.".format(movie))

    #                     #動画名から各種情報を取得
    #                     ruck_num, which_side, shoot_position, time_log, cam_num = movie.replace(".mp4", "").split("_")  #ラック番号, ラックの左右情報, 撮影位置番号, 撮影date, カメラナンバー
    #                     movie_info = [ruck_num, which_side, shoot_position, time_log, cam_num]
    #                     print("start_processing----------")
    #                     print("・ruck_num：{}\n・which_side：{}\n・shoot_position：{}\n・time_log：{}".format(ruck_num, which_side, shoot_position, time_log))
    #                     print("--------------------------")
                        
    #                     #mask_infoの作成-----------------------------------------------
    #                     #mask_info: ["ruck_num", "which_side", "shoot_position", "time_log", "x", "y", "group_num", "num_of_groups", "lamp_num", "num_of_lamps"]
    #                     stats_df =  part_normal_states.reindex(columns=["x", "y"]) # → stats_df...["x", "y"]

    #                     #グルーピング-----
    #                     def isInThreshold(value, center, threshold):
    #                         return (value < center + threshold) and (center - threshold < value)
                        
    #                     _stats_df = stats_df.copy()
    #                     _stats_df = _stats_df.values.tolist()
    #                     tmp = None
    #                     threshold = 100  #閾値 px

    #                     result_groups = []   #二次元配列 
    #                     while True:
    #                         if len(_stats_df) == 0:
    #                             break
    #                         tmp = _stats_df.pop(0) #pop...指定した値の要素を取得し、元のリストから削除する
    #                         y = tmp[1]  # 要素番号1＝y
    #                         group = [tmp]
    #                         for _tmp in _stats_df[:]:
    #                             if isInThreshold(_tmp[1], y, threshold):
    #                                 group.append(_tmp)
    #                                 _stats_df.remove(_tmp)
    #                         group = sorted(group)  # result_groupsを要素ごとにx（要素番号0）でソート
    #                         result_groups.append(group)
                        
    #                     grouped_stats = []  #再び２次元リストに戻す. その際所属グループのナンバーとランプナンバーを要素に入れこむ.
    #                     for k, group in enumerate(result_groups):
    #                         for l, each in enumerate(group):
    #                             each.insert(2,str(k))  #group_num
    #                             each.insert(3,None)  #num_of_groups（人グループを）
    #                             each.insert(4,str(l))  #lamp_num
    #                             each.insert(5,str(len(group)))  #num_of_groups
    #                             grouped_stats.append(each)
    #                     #-----グルーピング（終）



    #                     #曲座標変換--------------
    #                     # forでgrouped_statsを回して、i番目のx,i番目のy,i+1番目のX,i+1番目のYを取得して極座標の関数にかける
    #                     # 取得したr,θをリストに追加
    #                     # 最後のi番目は次のiがないので0でもNoneでも入れとく.その後不都合ないように
    #                     new_grouped_stats = []
    #                     for k, each in enumerate(grouped_stats):
    #                         if k == len(grouped_stats) - 1:
    #                             each.insert(6,str(0))  #r
    #                             each.insert(7,str(0))  #degree
    #                         else:
    #                             x = grouped_stats[k][0]
    #                             y = grouped_stats[k][1]
    #                             X = grouped_stats[k+1][0]
    #                             Y = grouped_stats[k+1][1]
    #                             r, degree = getxy_RD(x, y, X, Y)
    #                             each.insert(6,str(r))
    #                             each.insert(7,str(degree))
    #                         new_grouped_stats.append(each)
    #                     #-----------曲座標変換（終）

    #                     # 再度stats_dfとしてDF化
    #                     stats_df = pd.DataFrame(new_grouped_stats, columns=["x", "y", "group_num", "num_of_groups", "lamp_num", "num_of_lamps", "r", "degree"])
                        
    #                     #マスク情報作成
    #                     #stats_dfをベースにmovie_infoをインサートしていく
    #                     stats_df.insert(0, "ruck_num", movie_info[0])  #df自体が更新されるので再代入不要
    #                     stats_df.insert(1, "which_side", movie_info[1] )
    #                     stats_df.insert(2, "shoot_position", movie_info[2]  )
    #                     stats_df.insert(3, "time_log", movie_info[3] )

    #                     mask_info = stats_df


    #                     print("mask_info：\n", mask_info)
    #                     #-----------------------------------------------

    #                     frames = module.cut_frame.cut_frame(cap, param)  # get_frameでフレームを取得
    #                     undistort_frames = module.undistort_frames.undistort_frames(frames, movie_info) #補正
    #                     lamp_imgs = module.get_lamp_imgs.get_lamp_imgs(mask_info, undistort_frames, param)
    #                     part_normal_states = module.get_lamp_state.get_lamp_state(lamp_imgs, mask_info, param)

    #                 print("---------------------------------------------")
                    
    #             else:
    #                 pass

            
    #         # part_normal_staesからdeleteのところだけ飛ばして

            
    

    # new_normal_states = new_normal_states.reset_index(drop = True)
    # new_normal_states = new_normal_states.drop(index = 0)
    # new_normal_states = new_normal_states.reset_index(drop = True)
    # new_normal_states.to_csv("new_normal_states.csv")

    # delete_process = delete_process.reset_index(drop = True)
    # delete_process = delete_process.drop(index = 0)
    # delete_process = delete_process.reset_index(drop = True)
    # delete_process.to_csv("delete_process.csv")


























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
