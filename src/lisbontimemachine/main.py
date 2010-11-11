#!/usr/bin/env python
from google.appengine.ext import webapp
from google.appengine.ext.webapp import util

from google.appengine.api import urlfetch

import xml.etree.ElementTree as ET

token = '14IIACN92O60YV6L'
base = "http://cml-hub.mrnet.pt/CML_webservices/rest/%s" % token

def server_call(params):
    url = '%s/%s' % (base, params)
    result = urlfetch.fetch(url)
    if result.status_code == 200:
        return ET.XML(result.content)
    else:
        return None



class ListStuff(webapp.RequestHandler):
    def get(self):        
        latitude = self.request.get('latitude', '')
        longitude = self.request.get('longitude', '')
        url = 'collection/fotografias/articles/latitude/%s/longitude/%s' % (latitude, longitude)
        tree = server_call(url)
        element = tree.find("listArticles/articles")        
        for i in element.getchildren():            
            article_id = i.text
            
            article_element = server_call('collection/fotografias/article/%s' % article_id)
            article_title = article_element.findtext('getArticle/article/titulo')
            article_date = article_element.findtext('getArticle/article/data')
            article_image = article_element.findtext('getArticle/article/image')
            article_latitude = article_element.findtext('getArticle/article/latitude')            
            article_longitude = article_element.findtext('getArticle/article/longitude')
            
            output = """
<p>
<h1>%(article_title)s, %(article_date)s</h1>
<h2>%(article_longitude)s,%(article_latitude)s</h2>
<img src="%(article_image)s" alt="%(article_title)s"/>
</p>
"""  % locals()  
            
            self.response.out.write(output)

class MainHandler(webapp.RequestHandler):
    def get(self):
        self.response.out.write('<html><head><title>Lisbon Timemachine</title><body>LISBON TIMEMACHINE</body>')


def main():
    application = webapp.WSGIApplication([('/', MainHandler), ('/list', ListStuff)],
                                         debug=True)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()
