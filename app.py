import sqlite3
import requests
import re
import unicodedata
import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText


def setup_database(db_path: str) -> None:
    '''建立資料庫及定義資料表結構'''

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS "contacts" (
                "iid" INTEGER PRIMARY KEY AUTOINCREMENT,
                "name" TEXT NOT NULL,
                "title" TEXT NOT NULL,
                "email" TEXT NOT NULL UNIQUE
            );
        ''')
        conn.commit()


def scrape_contacts(url: str) -> dict:
    # content-type: text/html; charset=UTF-8
    # params = {
    #     "Action": "mobileloadmod",
    #     "Type": "mobile_rcg_mstr",
    #     "Nbr": "730"
    # }
    header = {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
    }

    response = requests.post(url, headers=header)
    # response = requests.post(URL, headers=header, data=params)

    # 抓取姓名
    pattern = re.compile(r'<div class="member_name"><a href="[^"]+">([^<]+)</a>')
    match_list = pattern.findall(response.text)
    names_list = list(match_list)

    # 抓取職稱
    pattern = re.compile(r'<div class="member_info_title"><i class="fas fa-briefcase"></i>職稱</div>\s*<div class="member_info_content">([^<]+)</div>'
)
    match_list = pattern.findall(response.text)
    titles_list = list(match_list)

    # 抓取 Email
    pattern = re.compile(r'<div class="member_info_content"><a href="mailto://([^"]+)">')
    match_list = pattern.findall(response.text)
    emails_list = list(match_list)

    # 合併爬取資料
    contacts = {
        'name': names_list,
        'title': titles_list,
        'email': emails_list
    }

    return contacts


def parse_contacts(contacts: dict) -> list:
    '''重組聯絡人資訊'''

    parsed_contacts = []

    for i in range(len(contacts['name'])):
        contact = {
            'name': contacts['name'][i],
            'title': contacts['title'][i],
            'email': contacts['email'][i]
        }
        parsed_contacts.append(contact)

    return parsed_contacts


def save_to_database(db_path: str, contacts: list) -> None:
    '''將爬取的聯絡資訊存入資料庫'''

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()

        for contact in contacts:
            cursor.execute('''
                INSERT INTO contacts (name, title, email)
                VALUES (?, ?, ?)
            ''', (contact['name'], contact['title'], contact['email']))

        conn.commit()


def save_to_database(db_path: str, contacts: list) -> None:
    '''將爬取的聯絡資訊存入資料庫'''

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()

        for contact in contacts:
            # 查詢是否已存在該 email
            cursor.execute('SELECT * FROM contacts WHERE email = ?', (contact['email'],))
            if cursor.fetchone() == None:  # 沒有記錄才插入
                cursor.execute('''
                    INSERT INTO contacts (name, title, email)
                    VALUES (?, ?, ?)
                ''', (contact['name'], contact['title'], contact['email']))

        conn.commit()


def display_contacts(contacts: list) -> str:
    """格式化輸出聯絡資料，使用固定寬度格式對齊輸出，可處理中英文對齊"""

    def get_display_width(text: str) -> int:
        """計算字串的顯示寬度，考慮到全形和半形字元"""
        return sum(2 if unicodedata.east_asian_width(char) in 'WF' else 1 for char in text)

    def pad_to_width(text: str, width: int) -> str:
        """將字串填充到指定的寬度"""
        current_width = get_display_width(text)
        padding = width - current_width
        return text + ' ' * max(0, padding)

    # 定義表頭和欄位寬度
    headers = ['姓名', '職稱', 'Email']
    widths = [15, 50, 45]  # 修改 Email 欄位的寬度

    # 生成表頭
    header_line = ''.join(pad_to_width(header, width) for header, width in zip(headers, widths))
    output = [header_line, "-" * sum(widths)]

    # 生成內容
    for contact in contacts:
        line = ''.join(
            pad_to_width(str(contact[key]), width)
            for key, width in zip(['name', 'title', 'email'], widths)
        )
        output.append(line)

    return "\n".join(output)



def on_button_click(entry_url: str) -> list:
    '''點選抓取按鈕後, 先爬取資料, 將其顯示在GUI上, 並存入資料庫'''
    get_contacts = parse_contacts(scrape_contacts(entry_url))
    contacts.insert(tk.END, f"{display_contacts(get_contacts)}\n\n\n")
    save_to_database(DB_PATH, get_contacts)


'''主程式'''
URL = "https://csie.ncut.edu.tw/content.php?key=86OP82WJQO"
# URL = "https://ai.ncut.edu.tw/p/412-1063-2382.php"
# URL = "https://ai.ncut.edu.tw/app/index.php?Action=mobileloadmod&Type=mobile_rcg_mstr&Nbr=730"
DB_PATH = "contacts.db"

setup_database(DB_PATH)

'''
    使用到的元件：ttk、Label、Entry、Button、ScrolledText、messagebox
    佈局方式：grid (留意元件的對齊方式還有 列/欄 的權重設定)
    視窗大小：640x480
'''

# 視窗
form = tk.Tk()                          # 建立視窗物件
form.title('聯絡資訊爬蟲')              # 視窗標題
form.geometry('640x480')                # 視窗預設大小
form.resizable(True, True)              # 長寬可改變
form.config(cursor="arrow")             # 游標形狀

# URL標籤
label = tk.Label(form, text="URL:", font=("Arial", 10))
label.grid(row=0, column=0, sticky="wn", ipady=5, padx=10, pady=5)

# URL輸入
entry = tk.Entry(font=("Arial", 10))
entry.insert(0, URL)  # default
entry.grid(row=0, column=1, ipady=1, padx=10, pady=5, sticky="we")

# 抓取按鈕
button = ttk.Button(form, text='抓取', command = lambda: on_button_click(entry.get()))
button.grid(row=0, column=2, ipadx=3, padx=10, pady=10, sticky="en")

# 聯絡資訊
contacts = ScrolledText(
    height=10,
    width=30,
    wrap=tk.NONE,
    font=("新細明體", 12),
    bg="white",  # 背景顏色
    fg="black",  # 文字顏色
)
contacts.grid(row=1, columnspan=3, ipadx=3, padx=10, pady=10, sticky="wesn")


# 剩餘空間
form.rowconfigure(1, weight=1)    # 設定第 1 列的權重為 1, 會取得所有剩餘空間
form.columnconfigure(1, weight=1) # 設定第 1 欄的權重為 1, 會取得所有剩餘空間

form.mainloop()
