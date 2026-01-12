import pygame

import requests

import threading

import time

import os

import json

import webbrowser

import io

import ctypes

import sys

import pyautogui

import cv2

import numpy as np

import pyperclip



# --- 1. SYSTEM CONFIGURATION ---

def resource_path(relative_path):

    """ Get absolute path to resource, works for dev and for PyInstaller """

    try:

        base_path = sys._MEIPASS

    except Exception:

        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)



# Windows DPI Awareness and App ID

try:

    myappid = 'albeda.terminal.v2.9' 

    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

    ctypes.windll.shcore.SetProcessDpiAwareness(1)

except:

    try: ctypes.windll.user32.SetProcessDPIAware()

    except: pass



os.environ['SDL_VIDEO_CENTERED'] = '1'



# --- 2. GLOBAL UTILITIES ---

global_logs = "" 



# Player lists state

player_page = 0 

PLAYERS_PER_PAGE = 20

players_list = []



def fetch_players(server_id):

    global players_list, show_players_win, player_page

    try:

        player_page = 0 

        url = f"https://api.battlemetrics.com/servers/{server_id}?include=player"

        r = requests.get(url, timeout=10).json()

        new_list = []

        if 'included' in r:

            for item in r['included']:

                if item['type'] == 'player':

                    name = item.get('attributes', {}).get('name', 'Unknown')

                    meta = item.get('meta', {})

                    hours = int(meta.get('timePlayed', 0) // 3600)

                    new_list.append({'name': name, 'hours': hours})

        players_list = sorted(new_list, key=lambda x: x['hours'], reverse=True)

        if not players_list:

            players_list = [{'name': 'No Players Found', 'hours': 0}]

        show_players_win = True

    except:

        players_list = [{'name': 'Error Loading', 'hours': 0}]

        show_players_win = True



def global_player_search(target_nickname):

    global global_logs, servers

    global_logs = f"SEARCHING: {target_nickname}..."

    found_on = []

    target = target_nickname.lower()

    for s in servers[:15]: 

        try:

            url = f"https://api.battlemetrics.com/servers/{s['id']}?include=player"

            r = requests.get(url, timeout=5).json()

            if 'included' in r:

                for p in r['included']:

                    if p['type'] == 'player':

                        p_name = p['attributes']['name']

                        if target in p_name.lower():

                            found_on.append(s['name'])

        except: pass

    global_logs = f"FOUND ON: {', '.join(found_on)}" if found_on else "PLAYER NOT FOUND IN TOP 15"



# --- 3. PYGAME INIT & ASSETS ---

pygame.init()

WIDTH, HEIGHT = 1000, 950

screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.HWSURFACE | pygame.DOUBLEBUF)

pygame.display.set_caption("Albeda Terminal")



try:

    icon_p = resource_path("icon.png")

    if os.path.exists(icon_p):

        pygame.display.set_icon(pygame.image.load(icon_p))

except: pass



clock = pygame.time.Clock()



COLOR_BG = (2, 5, 10); COLOR_CYAN = (0, 255, 255); COLOR_WHITE = (255, 255, 255)

COLOR_BLUE_DARK = (10, 30, 60); COLOR_GRAY = (150, 150, 150)

COLOR_GREEN = (0, 255, 100); COLOR_RED = (255, 50, 50)



font_header = pygame.font.SysFont("Consolas", 32, bold=True)

font_bold = pygame.font.SysFont("Consolas", 18, bold=True)

font_main = pygame.font.SysFont("Consolas", 16)



# --- 4. DATA HANDLING ---

if getattr(sys, 'frozen', False):

    BASE_DIR = os.path.dirname(sys.executable)

else:

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))



PROFILE_PATH = os.path.join(BASE_DIR, "user_profile.json")

is_registered = False; user_nickname = ""

reg_status = "" 



servers = []; search_query = ""; search_active = False

current_page = 0; SERVERS_PER_PAGE = 10 

show_players_win = False; selected_ip = None

is_running = False; app_running = True

latest_video_img = None; LAST_VIDEO_ID = ""; REMOTE_HEADER = "LOADING..."



# Configuration Links

TG_CHANNEL = "YOUR_CHANNEL_NAME"

CONFIG_URL = "https://raw.githubusercontent.com/YOUR_USER/YOUR_REPO/main/config.json"



if os.path.exists(PROFILE_PATH):

    try:

        with open(PROFILE_PATH, "r", encoding='utf-8') as f:

            data = json.load(f)

            user_nickname = data.get("nickname", "User")

            is_registered = True

    except: pass



# --- 5. BACKGROUND DATA UPDATER ---

def fetch_main_data():

    global servers, LAST_VIDEO_ID, latest_video_img, REMOTE_HEADER

    cache_path = os.path.join(BASE_DIR, "cached_preview.png")

    headers = {"User-Agent": "Mozilla/5.0"}



    while app_running:

        try:

            res = requests.get("https://api.battlemetrics.com/servers?filter[game]=vrising&page[size]=50&sort=-players", timeout=10)

            if res.status_code == 200:

                servers = [{"id": s['id'], "name": s['attributes']['name'], "pop": f"{s['attributes']['players']}/{s['attributes']['maxPlayers']}", "ip": f"{s['attributes']['ip']}:{s['attributes']['port']}"} for s in res.json()['data']]



            conf_res = requests.get(CONFIG_URL, timeout=5)

            if conf_res.status_code == 200:

                conf = conf_res.json()

                REMOTE_HEADER = conf.get("video_recommendation_title", "ANNOUNCEMENT")

                LAST_VIDEO_ID = conf.get("last_video_id", "").split('&')[0]



            tg_url = f"https://t.me/s/{TG_CHANNEL}"

            tg_res = requests.get(tg_url, headers=headers, timeout=10)

            if tg_res.status_code == 200 and 'background-image:url(\'' in tg_res.text:

                img_url = tg_res.text.split('background-image:url(\'')[-1].split('\')')[0]

                img_data = requests.get(img_url, timeout=10).content

                raw_img = pygame.image.load(io.BytesIO(img_data))

                f_surf = pygame.Surface((640, 360))

                scaled = pygame.transform.smoothscale(raw_img, (640, 480))

                f_surf.blit(scaled, (0, 0), (0, 60, 640, 360))

                latest_video_img = f_surf

        except: pass

        for _ in range(60):

            if not app_running: return

            time.sleep(1)



threading.Thread(target=fetch_main_data, daemon=True).start()



# --- 6. AUTOMATION MODULE ---

def type_unicode(text):

    for char in text:

        if char == " ":

            ctypes.windll.user32.keybd_event(0x20, 0, 0, 0)

            ctypes.windll.user32.keybd_event(0x20, 0, 2, 0)

        else:

            ctypes.windll.user32.keybd_event(0, ord(char), 0x0004, 0)

            ctypes.windll.user32.keybd_event(0, ord(char), 0x0004 | 0x0002, 0)

        time.sleep(0.01)



def vision_spam_worker():

    global is_running 

    template_path = resource_path("Loading.png")

    time.sleep(3)

    if not is_running: return

    full_command = f"connect {selected_ip}"

    first_attempt = True 

    

    while is_running and app_running:

        try:

            screen_shot = pyautogui.screenshot()

            screen_gray = cv2.cvtColor(np.array(screen_shot), cv2.COLOR_RGB2GRAY)

            template = cv2.imread(template_path, 0)

            if template is not None:

                res = cv2.matchTemplate(screen_gray, template, cv2.TM_CCOEFF_NORMED)

                if np.any(res >= 0.75):

                    is_running = False

                    break

        except: pass

        

        if is_running:

            type_unicode(full_command)

            ctypes.windll.user32.keybd_event(0x0D, 0, 0, 0)

            ctypes.windll.user32.keybd_event(0x0D, 0, 2, 0)

            if first_attempt:

                time.sleep(4.0); first_attempt = False

            else:

                time.sleep(1.4)



# --- 7. MAIN UI LOOP ---

try:

    while app_running:

        screen.fill(COLOR_BG); mx, my = pygame.mouse.get_pos()

        events = pygame.event.get()

        

        vid_rect = pygame.Rect((WIDTH - 560) // 2, 570, 560, 315)

        btn_start = pygame.Rect(WIDTH//2 - 100, 900, 200, 40)

        search_rect = pygame.Rect(110, 80, 690, 35)



        if not is_registered:

            reg_rect = pygame.Rect(WIDTH//2 - 200, HEIGHT//2 - 150, 400, 250)

            pygame.draw.rect(screen, (5, 15, 30), reg_rect)

            pygame.draw.rect(screen, COLOR_CYAN, reg_rect, 2)

            nick_surf = font_main.render(user_nickname + ("|" if time.time() % 1 > 0.5 else ""), True, COLOR_WHITE)

            screen.blit(nick_surf, (WIDTH//2 - 170, HEIGHT//2 - 28))

            btn_reg = pygame.Rect(WIDTH//2 - 100, HEIGHT//2 + 40, 200, 50)

            pygame.draw.rect(screen, COLOR_GREEN if btn_reg.collidepoint(mx, my) else (0, 150, 80), btn_reg, border_radius=10)

        else:

            screen.blit(font_header.render("ALBEDA TERMINAL 2.9", True, COLOR_WHITE), (WIDTH//2 - 160, 20))

            pygame.draw.rect(screen, COLOR_CYAN if search_active else COLOR_BLUE_DARK, search_rect, 1)

            filtered = [s for s in servers if search_query.lower() in s['name'].lower() or search_query in s['ip']]

            page_items = filtered[current_page*SERVERS_PER_PAGE : (current_page+1)*SERVERS_PER_PAGE]

            

            y_offset = 135

            for i, s in enumerate(page_items):

                y = y_offset + (i * 38)

                row_r = pygame.Rect(110, y, 780, 32)

                if s['ip'] == selected_ip: pygame.draw.rect(screen, (0, 80, 60), row_r)

                screen.blit(font_main.render(s['name'][:45], True, COLOR_CYAN), (120, y+7))

                screen.blit(font_bold.render(s['ip'], True, COLOR_WHITE), (680, y+7))



            if latest_video_img: 

                screen.blit(pygame.transform.smoothscale(latest_video_img, (560, 315)), (vid_rect.x, vid_rect.y))

            

            pygame.draw.rect(screen, COLOR_GREEN if is_running else (0, 180, 180), btn_start, border_radius=8)

            st_txt = font_bold.render("STOP (F8)" if is_running else "START (F8)", True, COLOR_BG)

            screen.blit(st_txt, (btn_start.centerx - st_txt.get_width()//2, btn_start.centery - 8))



        for event in events:

            if event.type == pygame.QUIT: app_running = False

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:

                if not is_registered:

                    if btn_reg.collidepoint(event.pos) and len(user_nickname) >= 3:

                        is_registered = True

                        with open(PROFILE_PATH, "w", encoding='utf-8') as f: json.dump({"nickname": user_nickname}, f)

                else:

                    if btn_start.collidepoint(event.pos) and selected_ip:

                        is_running = not is_running

                        if is_running: threading.Thread(target=vision_spam_worker, 