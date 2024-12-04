import sqlite3
import requests
import re
import unicodedata
import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
from tkinter import messagebox


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


def scrape_contacts(response: requests.Response) -> dict:
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


def show_network_error(error_massage: str) -> None:
    messagebox.showerror("網路錯誤", error_massage)


def on_button_click(entry_url: str) -> list:
    '''點選抓取按鈕後,
    1. 若網頁錯誤或網頁不存在, 跳出錯誤視窗
    2. 若連線正常, 則爬取資料,
    3. 將資料顯示在GUI上
    4. 將資料存入資料庫
    '''
    header = {
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
    }
    response = requests.get(entry_url, headers=header)

    try:
        response.raise_for_status()

    except requests.exceptions.ConnectionError as err:
        # 無法連接網站
        # https://csie1.ncut.edu.tw/content.php?key=86OP82WJQO
        terminal_err_msg = str(err) # 終端機回報的錯誤訊息存入err_msg
        '''
        HTTPSConnectionPool(host='csie1.ncut.edu.tw', port=443):
        Max retries exceeded with url:
        /content.php?key=86OP82WJQO (Caused by NameResolutionError("<urllib3.connection.HTTPSConnection object at 0x000001D53ED59D60>: Failed to resolve 'csie1.ncut.edu.tw' ([Errno 11001] getaddrinfo failed)"))
        '''
        domain_error = f"無法連接網站: {terminal_err_msg}"
        show_network_error(domain_error)

    except requests.exceptions.HTTPError:
        # 無法取得網頁
        # https://csie.ncut.edu.tw/content.php?kshidvblae
        page_not_found = "無法取得網頁: 404"
        show_network_error(page_not_found)

    else:
        # 正常連線
        get_contacts = parse_contacts(scrape_contacts(response))
        contacts.insert(tk.END, f"{display_contacts(get_contacts)}\n\n\n")
        save_to_database(DB_PATH, get_contacts)


'''主程式'''

URL = "https://csie.ncut.edu.tw/content.php?key=86OP82WJQO"

DB_PATH = "contacts.db"
setup_database(DB_PATH)

# 視窗
form = tk.Tk()                          # 建立視窗物件
form.title('聯絡資訊爬蟲')               # 視窗標題
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


# 以上程式在執行on_button_click()例外處理由終端機引發錯誤時, 並未執行show_network_error

# 舉例: 實測當 entry_url 為 https://csie1.ncut.edu.tw/content.php?key=86OP82WJQO 時, 終端機執行結果如下:

# Exception in Tkinter callback
# Traceback (most recent call last):
#   File "c:\Users\User\Desktop\Scripting_L\1131_Scripting_test3\env\Lib\site-packages\urllib3\connection.py", line 199, in _new_conn
#     sock = connection.create_connection(
#            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
#   File "c:\Users\User\Desktop\Scripting_L\1131_Scripting_test3\env\Lib\site-packages\urllib3\util\connection.py", line 60, in create_connection
#     for res in socket.getaddrinfo(host, port, family, socket.SOCK_STREAM):
#                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
#   File "C:\Python312\Lib\socket.py", line 976, in getaddrinfo
#     for res in _socket.getaddrinfo(host, port, family, type, proto, flags):
#                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
# socket.gaierror: [Errno 11001] getaddrinfo failed

# The above exception was the direct cause of the following exception:

# Traceback (most recent call last):
#   File "c:\Users\User\Desktop\Scripting_L\1131_Scripting_test3\env\Lib\site-packages\urllib3\connectionpool.py", line 789, in urlopen
#     response = self._make_request(
#                ^^^^^^^^^^^^^^^^^^^
#   File "c:\Users\User\Desktop\Scripting_L\1131_Scripting_test3\env\Lib\site-packages\urllib3\connectionpool.py", line 490, in _make_request
#     raise new_e
#   File "c:\Users\User\Desktop\Scripting_L\1131_Scripting_test3\env\Lib\site-packages\urllib3\connectionpool.py", line 466, in _make_request
#     self._validate_conn(conn)
#   File "c:\Users\User\Desktop\Scripting_L\1131_Scripting_test3\env\Lib\site-packages\urllib3\connectionpool.py", line 1095, in _validate_conn
#     conn.connect()
#   File "c:\Users\User\Desktop\Scripting_L\1131_Scripting_test3\env\Lib\site-packages\urllib3\connection.py", line 693, in connect
#     self.sock = sock = self._new_conn()
#                        ^^^^^^^^^^^^^^^^
#   File "c:\Users\User\Desktop\Scripting_L\1131_Scripting_test3\env\Lib\site-packages\urllib3\connection.py", line 206, in _new_conn
#     raise NameResolutionError(self.host, self, e) from e
# urllib3.exceptions.NameResolutionError: <urllib3.connection.HTTPSConnection object at 0x000001C3A6679A90>: Failed to resolve 'csie1.ncut.edu.tw' ([Errno 11001] getaddrinfo failed)

# The above exception was the direct cause of the following exception:

# Traceback (most recent call last):
#   File "c:\Users\User\Desktop\Scripting_L\1131_Scripting_test3\env\Lib\site-packages\requests\adapters.py", line 667, in send
#     resp = conn.urlopen(
#            ^^^^^^^^^^^^^
#   File "c:\Users\User\Desktop\Scripting_L\1131_Scripting_test3\env\Lib\site-packages\urllib3\connectionpool.py", line 843, in urlopen
#     retries = retries.increment(
#               ^^^^^^^^^^^^^^^^^^
#   File "c:\Users\User\Desktop\Scripting_L\1131_Scripting_test3\env\Lib\site-packages\urllib3\util\retry.py", line 519, in increment
#     raise MaxRetryError(_pool, url, reason) from reason  # type: ignore[arg-type]
#     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
# urllib3.exceptions.MaxRetryError: HTTPSConnectionPool(host='csie1.ncut.edu.tw', port=443): Max retries exceeded with url: /content.php?key=86OP82WJQO (Caused by NameResolutionError("<urllib3.connection.HTTPSConnection object at 0x000001C3A6679A90>: Failed to resolve 'csie1.ncut.edu.tw' ([Errno 11001] getaddrinfo failed)"))

# During handling of the above exception, another exception occurred:

# Traceback (most recent call last):
#   File "C:\Python312\Lib\tkinter\__init__.py", line 1968, in __call__
#     return self.func(*args)
#            ^^^^^^^^^^^^^^^^
#   File "c:\Users\User\Desktop\Scripting_L\1131_Scripting_test3\app.py", line 188, in <lambda>
#     button = ttk.Button(form, text='抓取', command = lambda: on_button_click(entry.get()))
#                                                              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
#   File "c:\Users\User\Desktop\Scripting_L\1131_Scripting_test3\app.py", line 134, in on_button_click
#     response = requests.get(entry_url, headers=header)
#                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
#   File "c:\Users\User\Desktop\Scripting_L\1131_Scripting_test3\env\Lib\site-packages\requests\api.py", line 73, in get
#     return request("get", url, params=params, **kwargs)
#            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
#   File "c:\Users\User\Desktop\Scripting_L\1131_Scripting_test3\env\Lib\site-packages\requests\api.py", line 59, in request
#     return session.request(method=method, url=url, **kwargs)
#            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
#   File "c:\Users\User\Desktop\Scripting_L\1131_Scripting_test3\env\Lib\site-packages\requests\sessions.py", line 589, in request
#     resp = self.send(prep, **send_kwargs)
#            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
#   File "c:\Users\User\Desktop\Scripting_L\1131_Scripting_test3\env\Lib\site-packages\requests\sessions.py", line 703, in send
#     r = adapter.send(request, **kwargs)
#         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
#   File "c:\Users\User\Desktop\Scripting_L\1131_Scripting_test3\env\Lib\site-packages\requests\adapters.py", line 700, in send
#     raise ConnectionError(e, request=request)
# requests.exceptions.ConnectionError: HTTPSConnectionPool(host='csie1.ncut.edu.tw', port=443): Max retries exceeded with url: /content.php?key=86OP82WJQO (Caused by NameResolutionError("<urllib3.connection.HTTPSConnection object at 0x000001C3A6679A90>: Failed to resolve 'csie1.ncut.edu.tw' ([Errno 11001] getaddrinfo failed)"))
