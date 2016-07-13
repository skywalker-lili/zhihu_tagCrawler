# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html

from __future__ import print_function, unicode_literals
import io
import simplejson as json

class ZhihuTagcrawlerPipeline(object):
    
    def close_spider(self, spider):
        """
        当spider结束任务时会执行这个method 
        第一： 把spider自带的保存tag结构的global dictionary 保存下来
        第二： 把tag items都写到一个json lite文件中去
        """
        # 1st: save tag structure to a json file
        with io.open("tag_structure.json", "w", encoding = "utf8") as outfile:
            data = json.dumps(spider.d, ensure_ascii=False, indent = 4)
            outfile.write(data)
        
        # 2nd: save all tag paths to a json lite file
        with io.open("tag_paths.jsonl", "w", encoding = "utf8") as outfile:
            for tag_path in spider.p:
                row = json.dumps(tag_path, ensure_ascii=False, sort_keys=True)
                print(row, file = outfile)
        
        # 3rd: save all tag items to a json lite file
        with io.open("tag_items.jsonl", "w", encoding = "utf8") as outfile:
            for tag_item in spider.l:
                row = json.dumps(tag_item, ensure_ascii=False)
                print(row, file = outfile)
        