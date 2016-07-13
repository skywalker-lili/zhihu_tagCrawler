# encoding: utf-8
# This spider crawls Zhihu.com's tag information specifically. It preserves the tag DAG structure using a nested dictionary

# A great many thanks to mylonly for its post "Scrapy模拟登陆知乎" on "http://www.jianshu.com/p/53af85a0ce18"
#  also thanks for Andrew_liu for its post "Python爬虫(七)--Scrapy模拟登录" on "http://www.jianshu.com/p/b7f41df6202d"

from __future__ import print_function, unicode_literals
import scrapy
import os
import time
from collections import defaultdict
import simplejson as json

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
    get_xsrf_url = "https://www.zhihu.com/signin" # url to visit first to get xsrf information
    login_url = "https://www.zhihu.com/login/email" # url to visit to login and get valid cookie
    start_urls = [
        "https://www.zhihu.com/topic/19776749/organize", 
        #"https://www.zhihu.com/topic/19554706/organize"
    ]
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Encoding": "gzip,deflate",
        "Accept-Language": "en-US,en;q=0.8,zh-TW;q=0.6,zh;q=0.4",
        "Connection": "keep-alive",
        "Content-Type":" application/x-www-form-urlencoded; charset=UTF-8",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36",
        "Referer": "http://www.zhihu.com"
    } 
    
    # Rules to enforce using cookie every time request a tag information page
    #restrict_xpaths = '//div[@id= "zh-topic-organize-page-children"]/ul/li/ul[@class= "zm-topic-organize-list"]',
    rules = [
        Rule(LinkExtractor(
                    allow= ['/topic/\d+/organize$', '/topic/\d+/organize/entire'], 
                    restrict_xpaths = ['//div[@id= "zh-topic-organize-child-editor"]', '//div[@class= "zm-topic-topbar"]']
                    ),
                process_request='request_tagOrPathPage', follow = True),
                # 符合rules，有follow = True，这样页面被parse_tagOrPathPage处理后，还是会被抓内部的link去继续crawling
    ] # 使用list，rules就自动成为iterable
    
    # 用来保存tag结构的大dictionary
    d = {"「根话题」":{}}
    
    # 用来保存每一条tag的list
    l = []
    
    # 用来保存每一条tag的paths的list
    p = []
    
    # Function to get the login response; Only called once
    # Scrapy刚启动时会call这个函数，函数的目的是拿到xsrf信息
    def start_requests(self):
        print("---"*5)
        print("start to request for getting the hidden info and cookie")
        print("---"*5)
        return [Request(self.get_xsrf_url, headers= self.headers, meta= \
                      {"cookiejar":1}, callback= self.post_login)]
    
    # Function to post a login form, notice it gets the xsrf string first before send the form
    # 这个函数会提取只有试图login知乎时才会得到的xsrf信息来构建一个登录form，然后得到登录成功的cookie
    def post_login(self, response):
        print("---"*5)
        print("preparing login...")
        print("---"*5)
        # Get the xsrf string
        xsrf = Selector(response).xpath('//div[@data-za-module="SignInForm"]//form//input[@name="_xsrf"]/@value').extract()[0]
        return FormRequest(self.login_url,
                                        meta = {"cookiejar": response.meta["cookiejar"]},
                                        headers = self.headers,
                                        # create form
                                        formdata = {
                                            "_xsrf": xsrf,
                                            "password": "My Zhihu Password",
                                            "email": "My Zhihu Email",
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
            yield Request(url, meta = {"cookiejar": 1}, headers = self.headers, \
                                    callback = self.parse, dont_filter = True) 
                                    # self.parse is the default parser used by CrawlSpider to apply rules
                                    # dont_filter = True so that this start_url request won't be filtered 
            print("A start_url has been requested:", url)
        print("---"*5)
        print("All start_urls cookies are have been requested!")
        print("---"*5)
    
    # Function to request tag information page or tag Path page
    # 函数先判断要request的是tag page 还是 path page。然后也按情况发出带上cookie和header的request；
    # CrawlSpider会首先用最低级的Request()去形成基础的request， 但是基础request无法通过zhihu.com反爬虫机制
    #     所以在rules中要求spider再用这个函数加工基础request成带cookie和header的能通过zhihu反爬虫机制的request
    def request_tagOrPathPage(self, request):
        
        if request.url.find("/entire") > 0: # the request is for a path page
            return Request(request.url, meta = {"cookiejar": 1, "dont_redirect": True, 'handle_httpstatus_list': [302]}, \
                    headers = self.headers, callback = self.parse_pathPage) 
        
        else: # this request is for a tag page
            return Request(request.url, meta = {"cookiejar": 1, "dont_redirect": True, 'handle_httpstatus_list': [302]}, \
                        headers = self.headers, callback = self.parse_tagPage)
     

    # 这个函数用来parse知乎的tag 页面
    # 它会找到并保存tag 的 parents 和 children； 最后模仿CrawlSpider自带的parse()来保证spider继续前进
    def parse_tagPage(self, response):
        sel = Selector(response)
        
        # tag的名字和链接
        name = sel.xpath('//h1[@class= "zm-editable-content"]/text()').extract()
        relative_link = sel.xpath('//div[@class= "zm-topic-topbar"]//a/@href').extract()
        
        # tag的parent
        parents = sel.xpath('//div[@id= "zh-topic-organize-parent-editor"]//a[@class= "zm-item-tag"]/text()').extract()
        parents = [s.replace("\n", "") for s in parents]
        
        # tag的children
        children = sel.xpath('//div[@id= "zh-topic-organize-child-editor"]//a[@class= "zm-item-tag"]/text()').extract()
        children = [s.replace("\n", "") for s in children]
        
        # 把tag item保存起来以备最后输出
        item = {}
        item["name"] = name
        item["relative_link"] = relative_link
        item["parents"] = parents
        item["children"] = children
        self.l.append(item)
        
        # 将item append到local file
        with io.open("tag_items.jsonl", "a", encoding = "utf8") as outfile: # "a" 表示appending mode
            row = json.dumps(item, ensure_ascii=False)
            print(row, file = outfile)
        
        # Mimic the return of CrawlSpider's default parse() so that the rules will be applied continueously
        #   in stead of just once on the start_urls
        return self.parse(response)
        
    
    # 这个函数用来parse tag 的path 页面
    # 它会找个对应tag的从根话题出发到自己(包含)的path。Path page不需要发散
    def parse_pathPage(self, response):
        #print("parse a path page!")
        sel = Selector(response)
        item = {}
        item["name"] = sel.xpath('//h1[@class= "zm-editable-content"]/text()').extract()
        
        # 找到Path
        paths = []
        for path_selector in sel.xpath('//div[@class= "zm-topic-tree"][1]/ul'):
            # 提取一条path并append到paths
            one_path = path_selector.xpath('.//a/text()').extract()
            paths.append(one_path)
        item["paths"] = paths
        
        #  将item append到local file
        with io.open("tag_paths_app.jsonl", "a", encoding = "utf8") as outfile: # "a" 表示是appending mode
            row = json.dumps(item, ensure_ascii=False, sort_keys=True)
            print(row, file = outfile)
        
        # 修改spider的tag structure dictionary
        outside = self.d # initially, the outside is the whole dictionary
        for path in paths:
            for i in path:
                try:
                    inside = outside[i]
                except KeyError:
                    inside = {}
                    outside[i] = inside
                outside = inside
            outside = self.d # reset the outside to whole dictionary
        
        # 将这个item的paths加入到spider的p dictionary中
        self.p.append(item)