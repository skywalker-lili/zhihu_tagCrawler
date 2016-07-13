# encoding: utf-8
# This spider crawls Zhihu.com's tag information specifically. It preserves the tag DAG structure using a nested dictionary

# A great many thanks to mylonly for its post "Scrapy模拟登陆知乎" on "http://www.jianshu.com/p/53af85a0ce18"
#  also thanks for Andrew_liu for its post "Python爬虫(七)--Scrapy模拟登录" on "http://www.jianshu.com/p/b7f41df6202d"

from __future__ import print_function, unicode_literals
import scrapy
import urllib2
import os
import re
import codecs
from collections import defaultdict

from scrapy.spiders import CrawlSpider,Rule
from scrapy.linkextractors import LinkExtractor
from scrapy.selector import Selector
from scrapy.http import Request
from scrapy.http import FormRequest
from scrapy.utils.response import open_in_browser
from zhihu_tagCrawler.items import ZhihuTagcrawlerItem

class ZhihuSpider(CrawlSpider):
    name = "zhihu"
    BASE_URL = "www.zhihu.com"
    start_urls = [
        "https://www.zhihu.com/topic/19776749/organize/entire",
        #"https://www.zhihu.com/topic/19778317/organize/entire",
        #"https://www.zhihu.com/topic/19778287/organize/entire",
        #"https://www.zhihu.com/topic/19560891/organize/entire",
        #"https://www.zhihu.com/topic/19618774/organize/entire",
        #"https://www.zhihu.com/topic/19776751/organize/entire",
        #"https://www.zhihu.com/topic/19778298/organize/entire",
    ]
    allow_domians = ["zhihu.com"]
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Encoding": "gzip,deflate",
        "Accept-Language": "en-US,en;q=0.8,zh-TW;q=0.6,zh;q=0.4",
        "Connection": "keep-alive",
        "Content-Type":" application/x-www-form-urlencoded; charset=UTF-8",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36",
        "Referer": "http://www.zhihu.com"
    } 
    
    custom_settings = {
        "REDIRECT_ENABLED": False 
    }
    
    # Rules to enforce using cookie every time request a tag information page
    rules = (
        Rule(LinkExtractor(allow='topic/\d+/organize/entire'), \
                process_request='request_tagInfoPage'),
    )
    
    # 用来保存tag结构的大dictionary，会在item pipeline中得到更新
    d = {}
    
    # 用来保存每一条tag的list，会在item pipeline中得到更新
    l = []
    
    
    # Function to get the login response; Only called once
    # Scrapy刚启动时会call这个函数，函数的目的是拿到xsrf信息
    def start_requests(self):
        print("---"*5)
        print("start to request the start_urls")
        print("---"*5)
        return [Request("https://www.zhihu.com", headers= self.headers, meta= \
                      {"cookiejar":1}, callback= self.post_login)]
    
    # Function to post a login form, notice it gets the xsrf string first before send the form
    # 这个函数会提取只有试图login知乎时才会得到的xsrf信息来构建一个登录form，然后得到登录成功的cookie
    def post_login(self, response):
        print("---"*5)
        print("preparing login...")
        print("---"*5)
        # Get the xsrf string
        xsrf = Selector(response).xpath('//div[@data-za-module="SignInForm"]//form//input[@name="_xsrf"]/@value').extract()[0]
        return FormRequest("https://www.zhihu.com/login/email",
                                        meta = {"cookiejar": response.meta["cookiejar"]},
                                        headers = self.headers,
                                        # create form
                                        formdata = {
                                            "_xsrf": xsrf,
                                            "password": "XXX",
                                            "email": "XXX",
                                            "remeber_me": "true",
                                        },
                                        callback = self.after_login,
                                        )
    
    # After login, this function request urls in the start_urls, initiate the whole process
    # 这个函数会给登录成功的cookie给start_urls, 这样start_urls也会带着cookie去request
    def after_login(self, response):
        for url in self.start_urls:
            # No need to callback since the rules has set the process_request parameter, 
            # which specifies a function to send the actual request. 
            yield Request(url, meta = {"cookiejar": 1}, headers = self.headers)
        print("---"*5)
        print("cookies are attached to start_urls!")
        print("---"*5)
    
    
    # Function to request tag information page
    # 这个函数是为了让scrapy爬后续的页面时也会带上cookie；
    # 在ZhihuSpider.rules中已经指明scrapy用这个函数来request符合rule的页面
    def request_tagInfoPage(self, request):
        return Request(request.url, meta = {"cookiejar": 1}, \
                    headers = self.headers)
        
    
    # Finally, the function to actually parse the tag information page
    # 这个函数才是真正接受知乎的tag结构页面并且parse页面的
    # 这个函数还会根据每一个tag的信息，修改spider用来保存tag structure的dictionary
    def parse_tagPage(self, response):
        sel = Selector(response)
        
        # tag的名字和链接
        name = sel.xpath('//*[@id= "zh-topic-title"]/h1/text()').extract()[0]
        relative_link = sel.xpath('//div[@class= "zm-topic-topbar"]//a/@href').extract()[0]
        content_link = "".join([self.BASE_URL, relative_link])
        structure_link = "".join([self.BASE_URL, relative_link, "/organize/entire"])
        
        # 找到tag的路径
        # 顺便抓取tag的parent
        paths = []
        parents = []
        for path_selector in sel.xpath('//div[@class= "zm-topic-tree"][1]/ul'):
            # 提取一条path并append到paths
            one_path = path_selector.xpath('.//a/text()').extract()
            paths.append(one_path)
            
            # 找到tag在这条path上的parent并append到parents
            if len(one_path) > 1: # 除了root tag， 其他tag的path都长过1
                parents.append(one_path[-2])
            else: # 专门为root tag写的case，因为它的path长度只有1， 它的parent就是本身
                parents.append(one_path[0])
        
        # tag的children
        children = sel.xpath('//li[@class = "zm-topic-organize-item"]/a/text()').extract()
        
        # 修改spider的tag structure dictionary
        outside = self.d
        for path in paths:
            for i in path:
                try:
                    inside = outside[i]
                except KeyError:
                    inside = {}
                    outside[i] = inside
                outside = inside
        
        # 新建一个tag item， 并赋值
        item = ZhihuTagcrawlerItem()
        
        item["name"] = name
        item["content_link"] = content_link
        item["structure_link"] = structure_link
        item["parents"] = parents
        item["children"] = children
        item["paths"] = paths
        
        print("---"*5)
        print(item["content_link"])
        print("---"*5)
        
        return item
        