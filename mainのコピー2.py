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
import module.make_gif

import inspect

import json

import math
import copy

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
    path = "1130/"
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


    #２点間を曲座標ベクトル変換
    def getxy_RD(x, y, X, Y):
        _x, _y = (X-x), (Y-y)
        r = math.sqrt(_x**2+_y**2)
        rad = math.atan2(_y, _x)
        degree = math.degrees(rad)
        #print(r, degree)
        return r, degree



    #正常状態csvのDataFrameでの読み込み
    normal_states = pd.read_csv("new_normal_states.csv", index_col=0)
    # --normal_states----------------------------------------
    # ruck_num	which_side, shoot_position, time_log, 
    # group_num	num_of_groups, lamp_num, num_of_lamps, x, y, 
    # r, degree, color, LF
    #--------------------------------------------------------
    # # get_lamp_imgs, get_lamp_state を make_mask_and_nomaly.py と共有するために引数normal_stateの形を整える（つまりmask_infoにする）
    # mask_infos = normal_states.drop(columns=["color", "LF", "lamp_num"])
    

    """
    #グローバルリスト（ここに諸情報を追加していき、最終的なアウトプットとする）
    current_states = pd.DataFrame([[0,0,0,0,0,0,0,0,0,0,0,0,0,0]], columns=[
        "ruck_num", "which_side", "shoot_position", "time_log",
        "group_num", "num_of_groups", "lamp_num", "num_of_lamps", "x", "y", 
        "normal_color", "normal_LF", 
        "current_color", "current_LF"
        ])
    """

    cur_lamp_info = []  #確定した全体情報はここに入れていく

    for i, movie in enumerate(files_list):
        print(i, "：", movie)
        cap =  cv2.VideoCapture(path + movie)

        if cap.isOpened()==False:
            print("[{}]：read error.".format(movie))
        else:
            print("[{}]：read success.".format(movie))

            # まずcurrentのこのmovieの
            # ------------------------------------------------------
            # ruck_num	which_side, shoot_position, time_log, 
            # group_num	num_of_groups, lamp_num, num_of_lamps, x, y
            # ------------------------------------------------------
            # だけ欲しいので make_mask_and_normal 同様の処理を行う

            #動画名から各種情報を取得
            ruck_num, which_side, shoot_position, time_log, cam_num = movie.replace(".mp4", "").split("_")  #ラック番号, ラックの左右情報, 撮影位置番号, 撮影date
            movie_info = [ruck_num, which_side, shoot_position, time_log, cam_num]
            print("start_processing----------")
            print("・ruck_num：{}\n・which_side：{}\n・shoot_position：{}\n・time_log：{}".format(ruck_num, which_side, shoot_position, time_log))
            print("--------------------------")

            frames = module.cut_frame.cut_frame(cap, param) #フレームを切り出す
            undistort_frames = module.undistort_frames.undistort_frames(frames, movie_info) #歪曲補正
            sum_img = module.sum_frames.sum_frames(undistort_frames, param) #集合画像作成
            #cv2.imwrite("sum_imgs_main/{}_{}_{}.jpg".format(ruck_num, which_side, shoot_position), sum_img)
            cur_obj_movie = module.get_mask_info.get_mask_info(sum_img, movie_info, param)
            """
            lamp_imgs = module.get_lamp_imgs.get_lamp_imgs(cur_obj_movie, undistort_frames, param)  #ランプ画像
            cur_state = module.get_lamp_state.get_lamp_state(lamp_imgs, cur_obj_movie, param)  #状態
            module.make_gif.make_gif(undistort_frames, cur_state, movie_info, param, "mask_gif_cur_aaa")
            """
            cur_obj_movie = cur_obj_movie.reindex(columns=[
                "ruck_num", "which_side", "shoot_position", "time_log", 
                "group_num", "num_of_groups", "lamp_num", "num_of_lamps", "x", "y"
                ])
            # --cur_obj_movie-----------------------------------------
            # ruck_num(0), which_side(1), shoot_position(2), time_log(3), 
            # group_num(4), num_of_groups(5), lamp_num(6), num_of_lamps(7), x(8), y(9),
            # -------------------------------------------------------
            #cur_obj_movie.to_csv("cur_obj_movie/{}_{}_{}".format(ruck_num, which_side, shoot_position))

            

            # normal_states からこの動画での対象となる part_ns_movie を取得
            part_ns_movie = normal_states.query('ruck_num == "{}" & which_side == "{}" & shoot_position == {}'.format(ruck_num, which_side, shoot_position))
            # --part_ns_movie------------------------------------------
            # ruck_num(0), which_side(1), shoot_position(2), time_log(3), 
            # group_num(4), num_of_groups(5), lamp_num(6), num_of_lamps(7), x(8), y(9), 
            # r(10), degree(11), color(12), LF(13)
            # ---------------------------------------------------------

            cur_lamp_movie = []   # cur_obj_movie を検証していき、特定したランプをここに入れていく

            # cur_obj_movie["num_of_groups"] と part_ns_movie["num_of_groups"] の一致
            if int(cur_obj_movie.iat[0,5]) != int(part_ns_movie.iat[0,5]):
                print("--------------------------------------------------------------------------------")
                print("参照情報のグループ数：", part_ns_movie.iat[0,5])
                print("取得情報のグループ数：", cur_obj_movie.iat[0,5])
                print("この撮影ポイントでのグループ数が一致しません. この撮影ポイントの検知をスキップします.")
                print("--------------------------------------------------------------------------------")
                
                part_ns_movie = part_ns_movie.values.tolist()
                for j in range(len(part_ns_movie)):
                    part_ns_movie[j][8], part_ns_movie[j][9] = 0, 0
                    part_ns_movie[j][10], part_ns_movie[j][11] = 0, 0
                    part_ns_movie[j][12], part_ns_movie[j][13] = "-", "-"
                for each_movie in part_ns_movie:
                    cur_lamp_info.append(each_movie)

                #gif画像生成
                # cur_lamp_movie をDF化
                part_ns_movie = pd.DataFrame(part_ns_movie, columns = [
                    "ruck_num", "which_side", "shoot_position", "time_log", 
                    "group_num", "num_of_groups", "lamp_num", "num_of_lamps", "x", "y", 
                    "r", "degree", "color", "LF"
                ])
                module.make_gif.make_gif(undistort_frames, part_ns_movie, movie_info, param, "mask_gif_cur")
                continue  #次のmovieに移る
            else:
                print("--------------------------------------------------------------------------------")
                print("参照情報のグループ数：", part_ns_movie.iat[0,5])
                print("取得情報のグループ数：", cur_obj_movie.iat[0,5])
                print("グループ数の一致を確認. グループごとの処理に移行します.")
                print("--------------------------------------------------------------------------------")


                for j in range(int(part_ns_movie.iat[0,5])):  #グループ回数分繰り返す
                    # それぞれグループごとに切り分ける
                    part_ns_group = part_ns_movie.query('group_num == {}'.format(j))
                    # --part_ns_group------------------------------------------
                    # ruck_num(0), which_side(1), shoot_position(2), time_log(3), 
                    # group_num(4), num_of_groups(5), lamp_num(6), num_of_lamps(7), x(8), y(9), 
                    # r(10), degree(11), color(12), LF(13)
                    # ---------------------------------------------------------
                    cur_obj_group = cur_obj_movie.query('group_num == {}'.format(j))

                    # DFだと操作が難しそうなので一度リストに戻す...
                    part_ns_group = part_ns_group.values.tolist()
                    cur_obj_group = cur_obj_group.values.tolist()

                    cur_lamp_group = copy.deepcopy(part_ns_group)  #多次元配列の値渡し. これを編集していって現在のランプ情報を作成していく.
                    cur_lamp_group[0][8], cur_lamp_group[0][9] =  cur_obj_group[0][8], cur_obj_group[0][9] #取得オブジェクトの0番を無条件で0版ランプ認定（強引）
                    cur_obj_group.pop(0)  #0番を入れたのでこっちからは消す
                    # --cur_lamp_group------------------------------------------
                    # ruck_num(0), which_side(1), shoot_position(2), time_log(3), 
                    # group_num(4), num_of_groups(5), lamp_num(6), num_of_lamps(7), x(8), y(9), 
                    # r(10), degree(11),
                    # color(12), LF(13)  ←この二つの情報は必要ないが標準リストから列を削除する良い方法が見つからないので、あとでDFにしてから削除する
                    # ---------------------------------------------------------



                    # cur_obj_groupの 0番ランプ の特定
                    """
                    zero_x, zero_y = part_ns_group[0][8], part_ns_group[0][9]
                    side =  100 # 範囲とする正方形の一辺
                    tmp = side/2
                    for k, each in enumerate(cur_obj_group):
                        obj_x, obj_y = cur_obj_group[k][8], cur_obj_group[k][9]
                        if (obj_x >= zero_x - tmp) & (obj_x <= zero_x + tmp) & (obj_y >= zero_y - tmp) & (obj_y <= zero_y + tmp):
                            # k番オブジェクトを0番ランプに確定。
                            print("{}番オブジェクトを0番ランプとして確定".format(k))
                            # k番ランプより前のレコードを cur_obj_group から削除する.
                            cur_lamp_group[0][8], cur_lamp_group[0][8] = cur_obj_group[k][8], cur_obj_group[k][9]
                            if k > 0:
                                del cur_obj_group[0:k+1]  #これによって cur_obj_group は 0番ランプの次のオブジェクトから入った状態になる
                            break
                        # もし該当するものが最後まで現れなかったとき、このグループの０番は認識されていなかった. このグループの処理をスキップする.
                        if k == len(cur_obj_group)-1 :
                            print("--------------------------------------------------------------------------------")
                            print("０番ランプが何らかの要因でキャッチできていません. このグループの処理をスキップします")
                            print("--------------------------------------------------------------------------------")
                            #-------------------------------------------------
                            #グループの処理を中断して次のグループに移るようにコードを書く
                            #-------------------------------------------------
                            for l in range(len(cur_lamp_group)):
                                cur_lamp_group[l][8], cur_lamp_group[l][9] = None, None
                                cur_lamp_group[l][10], cur_lamp_group[l][11] = None, None
                                part_ns_movie[l][12], part_ns_movie[l][13] = None, None
                            for each_group in cur_lamp_group:
                                cur_lamp_movie.append(each_group)
                            continue  #次のグループに移る
                    """


                    delta_r = 30   #rの許容範囲
                    delta_d = 10   #degreemの許容範囲

                    #_part_ns_group = part_ns_group.copy()  #このコピーは初期の順番を確認するために置く
                    #_cur_obj_group = cur_obj_group.copy()  #このコピーは初期の順番を確認するために置く

                    # # insert用の素材
                    # _ruck_num, _which_side, _shoot_position, _time_log = _part_ns_group[0][0], _part_ns_group[0][1], _part_ns_group[0][2], _part_ns_group[0][3]
                    # _group_num, _num_of_groups, _lamp_num, _num_of_lamps = _part_ns_group[0][4], _part_ns_group[0][5], _part_ns_group[0][6], _part_ns_group[0][7]
                    # #r, degree = _part_group_ns[][], _part_group_ns[][]




                    # 対象とするグループが適切か、各グループの０番オブジェクトのy値に範囲を持たせて検知する
                    



                    for k in range(len(part_ns_group)):  #ランプ個数分繰り返す
                        if k == len(part_ns_group) -1:  #kが最後のインデックスまで行ったら引けるベクトルもないので終了
                            break
                        else:
                            r, d = int(part_ns_group[k][10]), int(part_ns_group[k][11])
                            x, y = cur_lamp_group[k][8], cur_lamp_group[k][9]  #すでに確定しているランプから座標を持ってくる
                            print("part_ns_group\n", part_ns_group)
                            # part_ns_group と cur_lamp_group はどちらも正しい情報しか入っておらず、k番で連動

                            _cur_obj_group = cur_obj_group
                            #ここのループを脱出する迄に必ず一つ cur_lamp_group のレコードを編集している
                            for l in range(len(_cur_obj_group)):   #lで取り出すのは対象にしているk番の次の番号
                                X, Y = cur_obj_group[l][8], cur_obj_group[l][9]
                                R, D = getxy_RD(x, y, X, Y)  #取得情報の極座標
                                print("参照情報:{} / 取得情報:{} ---------------------".format(k, l))
                                print("x: {}, X: {}".format(x, X))
                                print("y: {}, Y: {}".format(y, Y))
                                print("r: {}, R: {}".format(r, R))
                                print("d: {}, D: {}".format(d, D))
                                print("Rr:{}".format(abs(R-r)))
                                print("Dd:{}".format(abs(D-d)))
                                print("---------------------------------")
                                if (abs(R-r) <= delta_r) & (abs(D-d) <= delta_d):  #abs...絶対値
                                #if (R >= r - delta_r) & (R <= r + delta_r):
                                    print("{}番オブジェクトを確定-------------------".format(k+1))
                                    cur_lamp_group[k+1][8], cur_lamp_group[k+1][9] = X, Y
                                    cur_lamp_group[k+1][10], cur_lamp_group[k+1][11] = R, D
                                    del cur_obj_group[0:l+1]  #l番まではうまく行ったのでそこまで消去
                                    break
                                elif (R > r):
                                    print("movie[{}_{}_{}], lamp[{}] が検出されませんでした. 補填します.".format(ruck_num, which_side, shoot_position, k+1))
                                    # k+1 番ランプは何らかの要因で認識されなかったので復活させる
                                    # part_ns_groupのk番ランプ と cur_lamp_groupのk番ランプ のずれ(dx,dy)を取得
                                    dx, dy = (cur_lamp_group[k][8] - part_ns_group[k][8]), (cur_lamp_group[k][9] - part_ns_group[k][9])
                                    # k番ランプずれ(x,y)を part_ns_groupのk+1番ランプ位置 に適用した位置を k+1番ランプとして cur_lamp_group に入れる
                                    insert_x, insert_y = (part_ns_group[k+1][8] + dx), (part_ns_group[k+1][9] + dy)
                                    cur_lamp_group[k+1][8], cur_lamp_group[k+1][9] = insert_x, insert_y
                                    cur_lamp_group[k+1][10], cur_lamp_group[k+1][11] = 10000, 10000
                                    del cur_obj_group[0:l]   #l-1番まではうまく行ったのでそこまで消去
                                    break
                                else:
                                    print("{}番オブジェクトはノイズ--------------------".format(l))
                                    

                    # cur_lamp_group を使ってランプの状態認識をしていく
                    # モジュールを使うために一度DFに変換（コードの都合上あとでリストに戻す）
                    cur_lamp_group = pd.DataFrame(cur_lamp_group, columns=[
                        "ruck_num", "which_side", "shoot_position", "time_log", 
                        "group_num", "num_of_groups", "lamp_num", "num_of_lamps", "x", "y", 
                        "r", "degree", "color", "LF"
                        ])
                    
                    frames = module.cut_frame.cut_frame(cap, param) #フレームを切り出す
                    undistort_frames = module.undistort_frames.undistort_frames(frames, movie_info) #補正
                    mask_info = cur_lamp_group.reindex(columns=[
                        "ruck_num", "which_side", "shoot_position", "time_log", 
                        "group_num", "num_of_groups", "lamp_num", "num_of_lamps", "x", "y"
                        ])
                    lamp_imgs = module.get_lamp_imgs.get_lamp_imgs(mask_info, undistort_frames, param)  #ランプ画像
                    cur_state = module.get_lamp_state.get_lamp_state(lamp_imgs, mask_info, param)  #状態
                    # cur_state-----------------------------------------------
                    # ruck_num(0), which_side(1), shoot_position(2), time_log(3), 
                    # group_num(4), num_of_groups(5), lamp_num(6), num_of_lamps(7), x(8), y(9), 
                    # color(10), LF(11)
                    # --------------------------------------------------------

                    # cur_lamp_group と cur_state をいい感じにconcatして
                    # cur_lamp_group ----------------------------------------
                    # ruck_num, which_side, shoot_position, time_log,
                    # group_num, num_of_groups, lamp_num, num_of_lamps, x, y,
                    # "r", "degree", "color", "LF"
                    # -------------------------------------------------------
                    # に整える.
                    cur_lamp_group = cur_lamp_group.reindex(columns=[
                        "ruck_num", "which_side", "shoot_position", "time_log", 
                        "group_num", "num_of_groups", "lamp_num", "num_of_lamps", "x", "y", 
                        "r", "degree"
                    ])
                    cur_state = cur_state.reindex(columns=["color", "LF"])
                    cur_lamp_group = pd.concat([cur_lamp_group, cur_state], axis=1)

                    cur_lamp_group = cur_lamp_group.values.tolist()

                    for each_group in cur_lamp_group:
                        cur_lamp_movie.append(each_group)
                    #print("cur_lamp_movie\n", cur_lamp_movie)
            


            """
            # cur_lamp_movie を使ってランプの状態認識をしていく
            # モジュールを使うために一度DFに変換（コードの都合上あとでリストに戻す）
            cur_lamp_info = pd.DataFrame(cur_lamp_info, columns=[
                "ruck_num", "which_side", "shoot_position", "time_log", 
                "group_num", "num_of_groups", "lamp_num", "num_of_lamps", "x", "y", 
                "r", "degree", "color", "LF"
                ])
            frames = module.cut_frame.cut_frame(cap, param) #フレームを切り出す
            undistort_frames = module.undistort_frames.undistort_frames(frames, movie_info) #補正
            mask_info = cur_lamp_info.reindex(columns=[
                "ruck_num", "which_side", "shoot_position", "time_log", 
                "group_num", "num_of_groups", "lamp_num", "num_of_lamps", "x", "y"
                ])
            lamp_imgs = module.get_lamp_imgs.get_lamp_imgs(mask_info, undistort_frames, param)  #ランプ画像
            cur_ns = module.get_lamp_state.get_lamp_state(lamp_imgs, mask_info, param)  #状態
            """

            #gif画像生成
            # cur_lamp_movie をDF化
            _cur_lamp_movie = pd.DataFrame(cur_lamp_movie, columns = [
                "ruck_num", "which_side", "shoot_position", "time_log", 
                "group_num", "num_of_groups", "lamp_num", "num_of_lamps", "x", "y", 
                "r", "degree", "color", "LF"
            ])
            module.make_gif.make_gif(undistort_frames, _cur_lamp_movie, movie_info, param, "mask_gif_cur")

            """
            # rev_part_movie_ns と rev_ns をいい感じにconcatして
            # new_normal_state --------------------------------------
            # ruck_num, which_side, shoot_position, time_log,
            # group_num, num_of_groups, lamp_num, num_of_lamps, x, y,
            # "r", "degree", "color", "LF"
            # -------------------------------------------------------
            # に整える.
            cur_ns = cur_ns.reindex(columns=["color", "LF"])
            cur_lamp_info = cur_lamp_info.reindex(columns=[
                "ruck_num", "which_side", "shoot_position", "time_log", 
                "group_num", "num_of_groups", "lamp_num", "num_of_lamps", "x", "y", 
                "r", "degree"
            ])
            cur_state_movie = pd.concat([cur_lamp_info, cur_ns], axis=1)
            
            # # rev_part_movie_ns を rev_ns にconcat
            # new_normal_states = pd.concat([new_normal_states, new_normal_state], axis=0)

            cur_lamp_movie = cur_state_movie.values.tolist()
            """



            for each_movie in cur_lamp_movie:
                cur_lamp_info.append(each_movie)
            #("cur_lamp_info\n", cur_lamp_info)
    
    cur_lamp_info = pd.DataFrame(cur_lamp_info, columns=[
        "ruck_num", "which_side", "shoot_position", "time_log", 
        "group_num", "num_of_groups", "lamp_num", "num_of_lamps", "x", "y", 
        "r", "degree", "color", "LF"
        ])

    cur_lamp_info.to_csv("cur_lamp_info.csv")



    
    #正常/異常判定
    #カラム名変更
    normal_states = normal_states.rename(columns = {"x":"nor_x", "y":"nor_y", "r":"nor_r", "degree":"nor_degree", "color":"nor_color", "LF":"nor_LF"})
    cur_lamp_info = cur_lamp_info.rename(columns = {"x":"cur_x", "y":"cur_y", "r":"cur_r", "degree":"cur_degree", "color":"cur_color", "LF":"cur_LF"})
    #連結
    cur_lamp_info = cur_lamp_info.reindex(columns = ["cur_x", "cur_y", "cur_r", "cur_degree", "cur_color", "cur_LF"])
    cur_lamp_info = pd.concat([normal_states, cur_lamp_info], axis=1)
    #カラム並び替え
    cur_lamp_info = cur_lamp_info.reindex(columns = [
        "ruck_num", "which_side", "shoot_position", "time_log", 
        "group_num", "num_of_groups", "lamp_num", "num_of_lamps", 
        "nor_x", "nor_y", "nor_r", "nor_degree", "nor_color", "nor_LF",
        "cur_x", "cur_y", "cur_r", "cur_degree", "cur_color", "cur_LF"
        ])



    cur_lamp_info["result"] = "a"  #新しいカラム[result]を定義&文字列で初期化
    for i, row in enumerate(cur_lamp_info.itertuples()):
        if row.nor_color == row.cur_color and row.nor_LF == row.cur_LF:
            cur_lamp_info.iat[i, 20] = "N"
        else:
            cur_lamp_info.iat[i, 20] = "Error"

    #csv出力
    cur_lamp_info.to_csv(filename)












if __name__ == "__main__":
    main()