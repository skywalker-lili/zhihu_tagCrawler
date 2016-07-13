# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

import scrapy


class ZhihuTagcrawlerItem(scrapy.Item):
    name = scrapy.Field() # tag的名字
    relative_link = scrapy.Field() # tag的相对链接
    parents = scrapy.Field() # tag的父tag们 
    children = scrapy.Field() # tag的子tag们
    
    
    

