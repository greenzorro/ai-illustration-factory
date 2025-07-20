'''
File: child_book_4_organize.py
Project: green
Created: 2025-04-07 10:00:26
Author: Victor Cheng
Email: greenzorromail@gmail.com
Description: 整理 src 目录下的图片到 TIFF 目录的子目录中
'''

import os
import sys

current_dir = os.path.dirname(__file__)
sys.path.insert(0, os.path.dirname(current_dir))

from child_book_utils import *

def main():
    # 执行图片整理
    organize_images_by_project()

if __name__ == "__main__":
    main() 