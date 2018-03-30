
# coding: utf-8

print('importing')
from math import hypot
import pandas as pd
from requests import get
import re
import telebot
import googlemaps
from config import manuals
import os
from flask import Flask, request
import botan
from lxml.html import fromstring
from lxml import cssselect
from datetime import datetime
# import urllib
# from io import StringIO
# from update import get_certs





token = os.environ.get('TOKEN')
API_KEY = os.environ.get('API_KEY')
BOTAN_KEY = os.environ.get('BOTAN_KEY')

#информация о свидетельствах
print('loading certificates')
data = pd.read_csv('doclist.csv', delimiter= ";", encoding = 'utf8')
# data = get_certs()

#информация о сервисных центрах
print('loadind service centeres')
services = pd.read_csv('service.csv', encoding='utf8', index_col=0)
services.drop(['geocode', 'address'], axis=1,inplace=True)
services['workhours'].fillna('', inplace = True)
useful_cols = ['city', 'type', 'address1', 'address2', 'tel', 'workhours']

#googlemaps
print('loadind gmaps')
gmaps = googlemaps.Client(key=API_KEY)

print('loading news')
def get_news():
    url_template = 'http://www.and-rus.ru/press/news/year/{}'
    news_headers = []
    news_dates = []
    news_urls = []
    year = datetime.now().year
    for i in range(2):
        dom = fromstring(get(url_template.format(year-i)).text)
        dom.make_links_absolute('http://and-rus.ru')
        news_headers += [dom.cssselect('.news_header a')[i].text for i in range(len(dom.cssselect('.news_header a')))]
        news_urls += [dom.cssselect('.news_header a')[i].get('href') for i in range(len(dom.cssselect('.news_header a')))]
        news_dates += [datetime.strptime(dom.cssselect('.news_date')[i].text,'%d.%m.%Y') for i in range(len(dom.cssselect('.news_date')))]
    
    news = dict(zip(news_dates, zip(news_headers, news_urls)))
    return news

news = get_news()
news_msg = ''
for key in sorted(news, reverse=True)[:3]:
    news_msg += """📄{}.{}.{}\n{}\n[Подробнее]({})\n\n""".format(key.day, key.month, key.year, news[key][0], news[key][1])

#инициализируем бота
print('Running bot')
bot = telebot.TeleBot(token)

server = Flask(__name__)


func_list = ['Свежие новости','Информация о поверке', 'Ближайший сервисный центр', 'Видеоинструкции']
keyboard_layout = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
for func in func_list:
    keyboard_layout.add(func)


videos_layout = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
for vid in list(manuals.keys()):
    videos_layout.add(vid)
videos_layout.add('Отмена')

start_msg = 'Чем я могу помочь?'


def manual_nearest_service(lat, lng):
    min_dist = 10000000
    nearest_sc = ''
    sc_description = ''
    for index in range(services.shape[0]):
        distance = hypot((lat-services.lat[index]), (lng-services.lng[index]))
        if distance < min_dist:
            min_dist = distance
            nearest_sc = index
    sc_longitude = services['lng'].loc[nearest_sc]
    sc_latitude = services['lat'].loc[nearest_sc]
    sc_description = '\n'.join(list(services[useful_cols].loc[nearest_sc]))
    return sc_longitude, sc_latitude, sc_description  

@bot.message_handler(commands=["start", 'menu'])
def dial_start(message):
    bot.send_message(message.chat.id, start_msg, reply_markup = keyboard_layout)
    botan.track(BOTAN_KEY, message.chat.id, message, 'Старт или меню')

@bot.message_handler(commands=['cat'])
def send_cat(message):
    bot.send_photo(message.chat.id, get(url='http://aws.random.cat/meow').json()['file'] , reply_markup = keyboard_layout)    
    botan.track(BOTAN_KEY, message.chat.id, message, 'Котик')
    
@bot.message_handler(content_types=['text'])
def response(message):
    geo_request = 'Пожалуйста, укажите свой город и адрес'
    sn_request = 'Введите серийный номер в формате [Модель][пробел][Серийный номер]'
    check_sn = 'Проверьте правильность ввода'
    manual_request = 'Выберите интересующую категорию'
    check_geo = 'Проверьте правильность адреса и попробуйте ещё'

    if message.text == 'Информация о поверке':
        markup = telebot.types.ForceReply(selective=False)
        bot.send_message(message.chat.id, sn_request, reply_markup=markup)
        markup = telebot.types.InlineKeyboardMarkup()
        cancel_button = telebot.types.InlineKeyboardButton(text="Меню", callback_data="Отмена")
        markup.add(cancel_button)
        bot.send_message(message.chat.id, 'Вернуться в меню', reply_markup=markup)
        botan.track(BOTAN_KEY, message.chat.id, message, 'Поверка')
    elif message.text == 'Ближайший сервисный центр':
        markup = telebot.types.ForceReply(selective=False)
        bot.send_message(message.chat.id, geo_request, reply_markup=markup) 
        markup = telebot.types.InlineKeyboardMarkup()
        cancel_button = telebot.types.InlineKeyboardButton(text="Меню", callback_data="Отмена")
        markup.add(cancel_button)
        bot.send_message(message.chat.id, 'Вернуться в меню', reply_markup=markup)
        botan.track(BOTAN_KEY, message.chat.id, message, 'Сервис')  
    elif message.text == 'Видеоинструкции':
        bot.send_message(message.chat.id, manual_request, reply_markup=videos_layout) 
        botan.track(BOTAN_KEY, message.chat.id, message, 'Видео')  
    elif message.text in manuals:
        bot.send_message(message.chat.id, manuals[message.text], reply_markup = keyboard_layout, parse_mode = 'Markdown')
        botan.track(BOTAN_KEY, message.chat.id, message, 'Видео ' + message.text)
    elif message.text == 'Свежие новости':
        bot.send_message(message.chat.id, news_msg, reply_markup=keyboard_layout, parse_mode = 'Markdown') 
        botan.track(BOTAN_KEY, message.chat.id, message, 'Новости')     
    elif message.reply_to_message != None:
        if (message.reply_to_message.text == sn_request) | (message.reply_to_message.text == check_sn):
            try:
                sku = re.findall(string=message.text, pattern = '[0-9]{3,4}')[0]
                if (sku == '911')&(len(re.findall(string=message.text, pattern = '[cC]+'))>0):
                    sku = '911c'
                serian_number = int(''.join(re.findall(string=message.text, pattern = '[0-9]{4,}')[-2:]))
                fltr = data.loc[(data['sku']==sku)&(data['start']<=serian_number)&(data['end']>=serian_number)]['url'].max()
                if str(fltr) != 'nan':
                    response = fltr
                    bot.send_message(message.chat.id, response, reply_markup = keyboard_layout)
                else:
                    response = check_sn
                    markup = telebot.types.ForceReply(selective=False)
                    bot.send_message(message.chat.id, response, reply_markup = markup)
            except IndexError:
                response = check_sn
                markup = telebot.types.ForceReply(selective=False)
                bot.send_message(message.chat.id, response, reply_markup = markup)
                markup = telebot.types.InlineKeyboardMarkup()
                cancel_button = telebot.types.InlineKeyboardButton(text="Меню", callback_data="Отмена")
                markup.add(cancel_button)
                bot.send_message(message.chat.id, 'Вернуться в меню', reply_markup=markup)
        elif (message.reply_to_message.text == geo_request) | (message.reply_to_message.text == check_geo):
            try:
                manual_location = message.text
                geocode = gmaps.geocode(manual_location)
                manual_lat = geocode[0]['geometry']['location']['lat']
                manual_lng = geocode[0]['geometry']['location']['lng']
                nearest_sc_longitude, nearest_sc_latitude, nearest_sc_descr = manual_nearest_service(manual_lat, manual_lng)
                bot.send_message(message.chat.id, nearest_sc_descr)
                bot.send_location(message.chat.id, longitude=nearest_sc_longitude, latitude=nearest_sc_latitude,  reply_markup=keyboard_layout)
            except IndexError:
                bot.send_message(message.chat.id, check_geo)
                markup = telebot.types.InlineKeyboardMarkup()
                cancel_button = telebot.types.InlineKeyboardButton(text="Меню", callback_data="Отмена")
                markup.add(cancel_button)
                bot.send_message(message.chat.id, 'Вернуться в меню', reply_markup=markup)
    elif message.text == 'Отмена':
        bot.send_message(message.chat.id, start_msg, reply_markup = keyboard_layout)
        botan.track(BOTAN_KEY, message.chat.id, message, 'Старт или меню')     
    else:
        bot.send_message(message.chat.id, start_msg, reply_markup = keyboard_layout)       

@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    # Если сообщение из чата с ботом
    if call.message:
        if call.data == "Отмена":
            bot.send_message(call.message.chat.id, start_msg, reply_markup = keyboard_layout)             

@server.route('/' + token, methods=['POST'])
def get_message():
    bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
    return "POST", 200


@server.route("/")
def web_hook():
    bot.remove_webhook()
    bot.set_webhook(url='https://infinite-waters-96978.herokuapp.com/' + token)
    return "CONNECTED", 200

server.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
