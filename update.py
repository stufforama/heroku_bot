
# coding: utf-8

# In[ ]:

import requests
from lxml.html import fromstring
from lxml import cssselect
import urllib
from io import StringIO
import pandas as pd
import re

# In[ ]:
def get_certs():

    url_template = 'http://and-rus.ru/service/{}_{}/'
    urls = []
    for author in ['calibrpressuread', 'termometrcalibration']:
        for page in range(1,200):
            urls.append(url_template.format(author, page))
            
    # flatten = lambda l: [item for sublist in l for item in sublist]


    # In[ ]:

    text = ''
    for url in urls:
        try:
            html = requests.get(url).text
            dom = fromstring(html)
            dom.make_links_absolute(url)
            css_elements = dom.cssselect('.menu-left')
            text += "\n".join([css_elements[t].text_content().strip() +';' + css_elements[t].get('href').strip() for t in range(3,len(css_elements))])
            if css_elements != []:
                text += '\n'
        except AttributeError:
            pass

    data = pd.read_csv(StringIO(text), sep=";",header=None, encoding = 'utf8')

    data.columns = ['text', 'url']
    pattern = '-[0-9]{3,4}'
    data['sku'] = data['text'].apply(lambda x: re.findall(string=x, pattern = pattern)[0].rsplit('-')[1])
    data.loc[data['sku']=='911', 'sku'] = data.loc[data['sku']=='911']['text'].apply(lambda x: '911c' if len(re.findall(string=x, pattern='[cC]+'))>0 else '911')
    data['start'] = data['text'].apply(lambda x: re.findall(string=x, pattern = '[0-9]{6,}')[0])
    data['end'] = data['text'].apply(lambda x: re.findall(string=x, pattern = '[0-9]{6,}')[1])
    data['start'] = pd.to_numeric(data['start'])
    data['end'] = pd.to_numeric(data['end'])
    data['url'] = data['url'].apply(lambda x: 'http://' + urllib.parse.quote(x.rsplit('//')[1]))
    data.drop(['text'], axis=1, inplace = True)
    return data

# data.to_csv('doclist.csv', sep=";",encoding = 'utf8')


