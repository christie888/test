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


# input : normal_state...["ruck_num", "which_side", "shoot_position", time_log, "x", "y", "group_num", "num_of_groups", "lamp_num", "num_of_lamps", "color", "LF"]
#         dir_name...gifを保存する先のファイル名
# output : gif画像
def make_gif(undistort_frames, normal_state, movie_info, param, gif_dir_name):
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
            #ランプ情報をputText（呼び出しもとファイルで処理を分ける）
            if (inspect.stack()[1].filename == "make_mask_and_normal.py") or (inspect.stack()[1].filename == "revision.py") :
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
            elif inspect.stack()[1].filename == "main.py":
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

    ruck_num, which_side, shoot_position, time_log, cam_num = movie_info
    undistort_frames = list(undistort_frames)  #gifにするのに標準リスト化
    clip = ImageSequenceClip(undistort_frames, fps=2)
    clip.write_gif('{}/{}_{}_{}_{}.gif'.format(gif_dir_name, ruck_num, which_side, shoot_position, time_log))



