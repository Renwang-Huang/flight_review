# Flight Review

This is a web application for flight log analysis. It allows users to upload
ULog flight logs, and analyze them through the browser.

## Installation and Setup

### 安装环境依赖
sudo apt-get install sqlite3 fftw3 libfftw3-dev
sudo apt-get install libatlas3-base

### clone源码
git clone --recursive https://github.com/PX4/flight_review.git

### 安装环境依赖
cd flight_review/app
pip install -r requirements.txt
./setup_db.py

### 开启网页终端
./serve.py --show

### 使用步骤
cd ~/px4-logviewer/src/flight_review/app
./serve.py --show

http://review.px4.io/plot_app?log=1c8d7407-c399-45a1-bb2b-bd4b0a02c314

review.px4.io ---> localhost:5006     log=1c8d7407-c399-45a1-bb2b-bd4b0a02c314 ---> GET[log]=da426514-ab3f-458b-9c6c-204b38316989
