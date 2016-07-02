
# This spider crawls Zhihu.com's tag information specifically. It preserves the tag DAG structure using a nested dictionary

# A great many thanks to mylonly for its post "Scrapy模拟登陆知乎" on "http://www.jianshu.com/p/53af85a0ce18"
#   also thanks for Andrew_liu for its post "Python爬虫(七)--Scrapy模拟登录" on "http://www.jianshu.com/p/b7f41df6202d"

import scrapy
import urllib2
import os
import re
import codecs
from collections import defaultdict

from scrapy.contrib.spiders import CrawlSpider,Rule
from scrapy.contrib.linkextractors.sgml import SgmlLinkExtractor
from scrapy.selector import Selector
from MySpider.items import zhihuItem
from scrapy.http import Request
from scrapy.http import FormRequest
from scrapy.utils.response import open_in_browser

class ZhihuSpider(scrapy.Spider):
    name = "zhihu"
    allowed_domains = ["www.zhihu.com"]
    start_urls = ["https://www.zhihu.com/topic/19776749/organize/entire"]
    
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
    rules = (
        Rule(SgmlLinkExtractor(allow=('/topic/\\d*/organize/entire')),process_request="request_tagInfoPage"),
    )
    
    # The dictionary to store tag DAG structure
    DAG_dict = {"根话题": {}}
    
    # A pool of urls to crawl so as long as this pool isn't empty, crawler will crawl
    url_toCrawl = ["https://www.zhihu.com/topic/19776749/organize/entire"]
    
    # Function to get the login response; Only called once
    def start_requests(self):
        return [Request("https://www.zhihu.com", headers= self.headers, meta= \
                      {"cookiejar":1}, callback= self.post_login)]
    
    # Function to post a login form, notice it gets the xsrf string first before send the form
    def post_login(self, response):
        self.log("preparing login...")
        # Get the xsrf string
        xsrf = Selector(response).xpath('//div[@data-za-module="SignInForm"]//form//input[@name="_xsrf"]/@value').extract()[0]
        self.log(xsrf)
        return FormRequest("https://www.zhihu.com/login/email",
                                        meta = {"cookiejar": response.meta["cookiejar"]},
                                        headers = self.headers,
                                        # create form
                                        formdata = {
                                            "_xsrf": xsrf,
                                            "password": "zhihu_19891217",
                                            "email": "skywalker.ljc@gmail.com",
                                            "remeber_me": "true",
                                        },
                                        callback = self.after_login,
                                        )
    
    # After login, this function request urls in the start_urls, initiate the whole process
    def after_login(self, response):
        while self.start_urls
            # No need to callback since the rules has set the process_request parameter, 
            # which specifies a function to send the actual request. 
            yield Request(url, meta = {"cookiejar": 1}, headers = self.headers)
    
    
    # Function to request tag information page
    def request_tagInfoPage(self, request):
        return Request(request.url, meta = {"cookiejar": 1}, headers = self.headers, callback = self.parse_tagPage)
        
    
    # Finally, the function to actually parse the tag information page
    def parse_tagPage(self, response):
        sel = Selector(response)
        # Selects links to crawl from this response page
        links = sel.xpath('//li[@class = "zm-topic-organize-item"]')
        
        self.start_urls.extend()
        
        def parse():
            
        