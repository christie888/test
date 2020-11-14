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






    #新しい情報を






if __name__ == "__main__":
    main()






