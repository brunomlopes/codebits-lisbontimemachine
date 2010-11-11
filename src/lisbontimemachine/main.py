#!/usr/bin/env python
import os

from google.appengine.ext import webapp
from google.appengine.ext.webapp import util

from google.appengine.api import urlfetch

import xml.etree.ElementTree as ET
from django.utils import simplejson


token = '14IIACN92O60YV6L'
base = "http://cml-hub.mrnet.pt/CML_webservices/rest/%s" % token

def server_call(params):
    url = '%s/%s' % (base, params)
    result = urlfetch.fetch(url)
    if result.status_code == 200:
        return ET.XML(result.content)
    else:
        return None

def server_list_photos(latitude, longitude):
    url = 'collection/fotografias/articles/latitude/%s/longitude/%s' % (latitude, longitude)
    return server_call(url)

def server_get_photo(article_id):
    return server_call('collection/fotografias/article/%s' % article_id)

def get_image_elements(latitude, longitude):
    tree = server_list_photos(latitude, longitude)
    element = tree.find("listArticles/articles")
    image_elements = []      
    for i in element.getchildren():            
        article_id = i.text        
        article_element = server_get_photo(article_id)
        photo_item = {
            'id': article_id,
            'title': article_element.findtext('getArticle/article/titulo'),
            'date': article_element.findtext('getArticle/article/data'),
            'image_url': article_element.findtext('getArticle/article/image'),
            'latitude': article_element.findtext('getArticle/article/latitude'),            
            'longitude': article_element.findtext('getArticle/article/longitude')
        }
        
        image_elements.append(photo_item)
    return image_elements


image_element_html_template = """
<p>
<h1>%(title)s, %(date)s</h1>
<h2>%(longitude)s,%(latitude)s</h2>
<img src="%(image_url)s" alt="%(title)s"/>
</p>
"""

class ListHTML(webapp.RequestHandler):
    def get(self):        
        latitude = self.request.get('latitude', '')
        longitude = self.request.get('longitude', '')
        for image_element in get_image_elements(latitude, longitude):
            self.response.out.write(image_element_html_template % image_element)

class ListJSON(webapp.RequestHandler):
    def get(self):        
        latitude = self.request.get('latitude', '')
        longitude = self.request.get('longitude', '')
        self.response.headers["Content-Type"] = "application/json"
        self.response.out.write(simplejson.dumps(get_image_elements(latitude, longitude)))

class MainHandler(webapp.RequestHandler):
    def get(self):
        path = os.path.join(os.path.dirname(__file__), 'static/index.html')        
        self.response.out.write(open(path, 'r').read())


def main():
    application = webapp.WSGIApplication([('/', MainHandler), ('/list', ListHTML), ('/list.json', ListJSON)],
                                         debug=True)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()
