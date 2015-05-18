

THREAD_REQUIERD = 5
_inputs = [
    {
        'http://www.bbc.com': [
            {'class': 'hero_title'},
            {'class': 'module_title'}
        ]
    },
    {
        'http://www.smashingmagazine.com/': [
            {'rel': 'bookmark'}
        ]
    }
]


import time
import redis
import threading
import requests
import BeautifulSoup
import logging


logging.basicConfig(level=logging.INFO,
                    format='(%(threadName)-10s) %(message)s',
                    )


class Redis(object):

    def __init__(self, host='127.0.0.1', port=6379, db=0):
        super(Redis, self).__init__()
        self.__pool = redis.ConnectionPool(host=host, port=port, db=db)
        self.connection = redis.Redis(connection_pool=self.__pool)


class RedisStorage(Redis):

    def __init__(self):
        super(RedisStorage, self).__init__()

    def store(self, key, data):
        self.connection.set('_key', data)


class DataCrawler(threading.Thread):

    def __init__(self, web_xml_queue):
        super(DataCrawler, self).__init__()
        self.web_xml_queue = web_xml_queue

    def run(self):
        while True:
            xml_data, elements = self.web_xml_queue.get()
            _data = {}
            for e in elements:
                if isinstance(e, dict):
                    _data[e.items()[0][1]] = [x.getText() for x in xml_data.findAll(attrs=e)]
                else:
                    _data[e] = xml_data.findAll(e)
            print _data
            self.web_xml_queue.task_done()


class XMLData(threading.Thread):

    def __init__(self, web_data_queue, web_xml_queue):
        super(XMLData, self).__init__()
        self.web_data_queue = web_data_queue
        self.web_xml_queue = web_xml_queue

    def run(self):
        while True:
            url, elements = self.web_data_queue.get()
            logging.info('Processing data from %s for %s' % (url, elements))
            xml_data = BeautifulSoup.BeautifulSoup(requests.get(url).text)
            self.web_xml_queue.put((xml_data, elements))
            self.web_data_queue.task_done()


class Crawler(threading.Thread):

    def __init__(self, web_url_queue, web_data_queue):
        super(Crawler, self).__init__()
        self.web_data_queue = web_data_queue
        self.web_urls_queue = web_urls_queue

    def run(self):
        while True:
            meta = self.web_urls_queue.get()
            url, elements = meta.items()[0]
            self.web_data_queue.put((url, elements))
            self.web_urls_queue.task_done()


from Queue import Queue
web_urls_queue = Queue()
web_data_queue = Queue()
web_xml_queue = Queue()

if __name__ == '__main__':
    start = time.time()
    threads = []
    for i in range(THREAD_REQUIERD):
        crawler = Crawler(web_urls_queue, web_data_queue)
        crawler.setDaemon(True)
        threads.append(crawler)
        crawler.start()

        cruncher = DataCrawler(web_xml_queue)
        cruncher.setDaemon(True)
        threads.append(cruncher)
        cruncher.start()

        cruncher = XMLData(web_data_queue, web_xml_queue)
        cruncher.setDaemon(True)
        threads.append(cruncher)
        cruncher.start()

    for _input in _inputs:
        web_urls_queue.put(_input)

    web_urls_queue.join()
    web_data_queue.join()
    web_xml_queue.join()

    print logging.info('elapsed time: %s' % (time.time() - start))
