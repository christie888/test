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


def main():
    """
    revision = pd.read_excel("revision.xlsx",sheet_name="change_info_and_delete", header=0, index_col=0)  #revision.xlsxをdfに格納
    delete_index = revision[revision['delete'].notnull()].index #revisionのNANでないものインデックスだけ取得（mask_infoのインデックス指定削除に使う）
    print("------------------")
    print(delete_index)
    print("------------------")

    #deleteカラムがNANのものだけ抽出
    revision = revision[revision['delete'].isnull()]  
    #revision = revision.reset_index()  #インデックスを振り直す
    #revisionをnormal_state.csvに上書き
    print(revision)
    revision.to_csv('normal_state.csv')

    #mask_info = pd.read_csv("mask_info.csv", index_col=None, names = ('ruck_num', 'L/R', 'shoot_position', 'time_log', 'x', 'y'))  #mask_info.csvをdf取得→mask_info
    mask_info = pd.read_csv("mask_info.csv", header=None)  #mask_info.csvをdf取得→mask_info
    mask_info = mask_info.drop(delete_index)  #mask_infoから先ほど取得したインデックスのレコードを削除
    #mask_info = mask_info.reset_index(drop=True)
    #mask_info（新）をmask_info.csvに上書き
    mask_info.to_csv('mask_info.csv')
    print(mask_info)
    """

    # normal.csvの編集（削除するオブジェクトをレコードごと消去 / 認識オブジェクトの追加）を適用させる

    # 編集後のnormal.csvを読み込み
    normal_states = pd.read_csv("normal_states.csv", index_col=0)
    print(normal_states)
    # 編集後のadditional.pyを読み込み
    add = pd.read_csv("additional.csv")

    new_normal_states = pd.DataFrame([[0,0,0,0,0,0,0,0,0]], columns=["ruck_num", "which_side", "shoot_position", "time_log", "ramp_num", "x", "y", "color", "LF"])

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
                    # その(x, y)をnormal_statesのmovie情報に該当する箇所の最初のindexに挿入する、どうせ下で整地されるのでramp_numは0で統一、本indexがどうなるのかは作業しながら観察
                    part_normal_states = part_normal_states.append({"ruck_num":ruck_num_add, "which_side":which_side_add, "shoot_position":shoot_position_add, "time_log":time_log_add, "ramp_num":0, "x":x, "y":y, "color":color, "LF":LF}, ignore_index=True)
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
                        # その(x, y)をnormal_statesのmovie情報に該当する箇所の最初のindexに挿入する、どうせ下で整地されるのでramp_numは0で統一、本indexがどうなるのかは作業しながら観察
                        part_normal_states = part_normal_states.append({"ruck_num":ruck_num_add, "which_side":which_side_add, "shoot_position":shoot_position_add, "time_log":time_log_add, "ramp_num":0, "x":x, "y":y, "color":color, "LF":LF}, ignore_index=True)
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
        
    new_normal_states = new_normal_states.reset_index()
    new_normal_states = new_normal_states.drop(index = 0)
    new_normal_states = new_normal_states.reset_index()

    # インデックスを振り直す
    #new_normal_states = new_normal_states.reset_index(drop = True)

    #print(normal_states)
    # normal_state.csvに再保存
    print(new_normal_states)
    new_normal_states.to_csv("normal_states.csv")


if __name__ == "__main__":
    main()
