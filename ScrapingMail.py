#!/usr/bin/env python
# coding: utf-8

# 1. 「小説家になろう」の対象小説に最新話が更新されているかどうかを判定
# 2. 更新されている小説リストと前日の確認後に更新されている話を一覧形式でメール送信
#     - 小説名・タイトル・更新日時・URL

from logging import getLogger, StreamHandler, DEBUG
logger = getLogger(__name__)
handler = StreamHandler()
handler.setLevel(DEBUG)
logger.setLevel(DEBUG)
logger.addHandler(handler)
logger.propagate = False

import os
import sys
import time
import datetime
from urllib.request import urlopen
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.header import Header

# --------------------------------------
# 作品ページのURLを指定（コメントアウト・コメントインで指定できるようにしています）
url_list = [
    "https://ncode.syosetu.com/n2267be/" # Ｒｅ：ゼロから始める異世界生活
    ,
#     "https://ncode.syosetu.com/n6316bn/" # 転生したらスライムだった件
#     ,
    "https://ncode.syosetu.com/n2031cu/" # 異世界転移で女神様から祝福を！　～いえ、手持ちの異能があるので結構です～
#     ,
#     "https://ncode.syosetu.com/n3009bk/" # 盾の勇者の成り上がり
    ,
    "https://ncode.syosetu.com/n6475db/" # 私、能力は平均値でって言ったよね！
#     ,
#     "https://ncode.syosetu.com/n5881cl/" # 賢者の孫
           ]
# --------------------------------------

MAILADDRESS = sys.argv[1]
MY_SECRET_PASSWORD = sys.argv[2]

from_address = MAILADDRESS
to_address = sys.argv[3]

SMTP_SERVER = sys.argv[4]
PORT_NUMBER = int(sys.argv[5])

delay_days = 1 # 通知頻度(日)

def main():
    """
    メイン処理
    """
    
    new_stories = {}

    # 各作品に処理を実行
    for url in url_list:
        
        html = urlopen(url)
        print('access {} ...'.format(url))
        bs_obj = BeautifulSoup(html,"html.parser")
        time.sleep(2)
        
        # 前回通知以降に更新された話のリストを抽出
        new_story_list = []
        
        for no in range(len(bs_obj.findAll("dd",{"class":"subtitle"})))[::-1]:
            # 作品ページから指定した話の情報を抜き出す
            story_info = get_story_info(bs_obj, no)
            # 前回の通知よりも後に話が公開されたかどうかを判定
            if is_new(story_info, delay_days):
                new_story_list.append(story_info)
                print("New: {}".format(story_info['url']))
            else:
                break

        new_story_list = new_story_list[::-1]

        novel_title = get_novel_title(bs_obj)
        
        if new_story_list:
            new_stories[novel_title] = new_story_list
    
    if new_stories:
        # メールの件名・本文を生成
        mail_subject, mail_body = create_mail_text(new_stories)
        # メール通知
        send_mail(from_address, to_address, mail_subject, mail_body)
    else:
        print('最新話の公開はありません。')


def get_novel_title(bs_obj):
    """
    作品名を抽出
    """
    novel_title = bs_obj.findAll("p",{"class":"novel_title"})[0].get_text()

    return novel_title


def get_story_info(bs_obj, story_no):
    """
    作品ページから指定した話の情報を抜き出す
    """
    novel_title = get_novel_title(bs_obj)

    story_url =  "https://ncode.syosetu.com" + bs_obj.findAll("dd",{"class":"subtitle"})[story_no].findAll("a")[0].attrs["href"]
    story_info = {
        "title": bs_obj.findAll("dd",{"class":"subtitle"})[story_no].findAll("a")[0].get_text(),
        "date": bs_obj.findAll("dt",{"class":"long_update"})[story_no].get_text().replace('\n', '').replace('（改）', ''),
        "url": story_url,
        "novel_title": novel_title,
        }

    return story_info


def is_new(story_info, delay_days):
    """
    前回の通知よりも後に話が公開されたかどうかを判定
    """
    story_datetime = datetime.datetime.strptime(story_info["date"], '%Y/%m/%d %H:%M')
    pre_scraping_datetime = datetime.datetime.now() - datetime.timedelta(days=delay_days) # 前回の通知時点
    
    return story_datetime > pre_scraping_datetime


def create_mail_text(new_stories):
    """
    メールの件名・本文を作成
    """
    today = datetime.datetime.now()

    mail_subject = '{}の更新お知らせ【小説家になろう】'.format(today.strftime('%Y-%m-%d %H:%M'))

    mail_body = '[{}]～[{}] 公開分\n\n'.format((datetime.datetime.now() - datetime.timedelta(days=delay_days)).strftime('%Y-%m-%d %H:%M'), today.strftime('%Y-%m-%d %H:%M'))

    for new_story_title, new_story in new_stories.items():
        mail_body += '【{}】------\n'.format(new_story_title)
        for new in new_story:
            mail_body += '{}\n[{} 公開]\n{}\n\n'.format(new['title'], new['date'], new['url'])
            
    return mail_subject, mail_body


def send_mail(from_address, to_address, mail_subject, mail_body):
    """
    メール通知
    """
    # サーバーと接続
    smtp_obj =smtplib.SMTP_SSL(SMTP_SERVER, PORT_NUMBER)
    smtp_obj.ehlo() # サーバーとの接続を確立
    smtp_obj.login(MAILADDRESS, MY_SECRET_PASSWORD) # SMTPサーバーにログイン

    # 日本語のメッセージを送信するための記述
    charset = 'UTF-8'
    mail_text = MIMEText(mail_body, 'plain', charset)
    mail_text['Subject'] = Header(mail_subject.encode(charset), charset)
    mail_text = mail_text.as_string()

    # メール送信
    try:
        send_result = smtp_obj.sendmail(
            from_address,
            to_address,
            mail_text)
        print('Sending {}...'.format(to_address))
        time.sleep(1)
    finally:
        smtp_obj.quit() # サーバーとの接続を切断
        print('サーバーとの接続を切断。')

    # メール送信失敗時の結果を表示
    if send_result:
        for key in send_result.keys():
            print('{}へのメール送信失敗。'.format(key))
    else:
        print('送信したメール本文\n\nSubject: {}\n\nMessage: {}'.format(mail_subject, mail_body))


if __name__ == '__main__':
    main()
