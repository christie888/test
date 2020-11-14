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

import module.get_ramp_imgs
import module.get_ramp_state



def main():
    
    
    a = [[1,2,3],[4,5,6],[1,2,9],[1,2,12],[1,14,15]]
    df = pd.DataFrame(a, columns = ["a","b","c"])
    print(df)
    print(df[(df["a"] == 1) & (df["b"] == 2)])



    # delete_index=[2,3]
    # a = a.drop(index=delete_index)
    # print(a)
    # a = a.reset_index(drop=True)
    # print(a)

    #a.to_csv("test.csv")
    
    
    """
    a = [[1,2,3],[4,5,6],[7,8,9]]
    df = pd.DataFrame(a, columns = ["a","b","c"])
    print(a)
    df.insert(0, 'd', 'info')
    print(df)
    """

    """
    a = []
    print(a)
    b = [[1,2,3], [4,5,6]]
    print(a+b)
    c = [[2,3,4], [5,6,7]]
    print(a+b+c)
    """



    """
    x = []

    a = [1]
    x = x+a
    x.append(1)
    x.append(2)
    x.append(3)
    print(x)
    print("aaa")
    """





if __name__ == "__main__":
    main()

