#!/usr/bin/env python
import os

from google.appengine.ext import webapp
from google.appengine.ext.webapp import util

from google.appengine.api import urlfetch
from google.appengine.ext import db
from google.appengine.api import users

import xml.etree.ElementTree as ET
from django.utils import simplejson
from google.appengine.api import memcache

import logging


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
    
    article_ids = memcache.get('photos_%s_%s' % (latitude, longitude))
    if not article_ids:
        logging.error('cache miss for photo list %s %s', latitude, longitude)
        tree = server_list_photos(latitude, longitude)
        element = tree.find("listArticles/articles")    
        article_ids = [i.text for i in element.getchildren()]
        memcache.set('photos_%s_%s' % (latitude, longitude), article_ids, 60 * 10)
        
    image_elements = []    
    for article_id in article_ids:            
        photo_item = memcache.get('photo_%s' % article_id)
        if not photo_item:
            logging.error('cache miss for photo item %s', article_id)
            article_element = server_get_photo(article_id)
            photo_item = {
                'id': article_id,
                'title': article_element.findtext('getArticle/article/titulo'),
                'date': article_element.findtext('getArticle/article/data'),
                'image_url': article_element.findtext('getArticle/article/image'),
                'latitude': article_element.findtext('getArticle/article/latitude'),            
                'longitude': article_element.findtext('getArticle/article/longitude')
            }
            
            accepted = AcceptedSuggestion.get_by_key_name(article_id)
            if accepted is not None:
                suggestion = accepted.suggestion
                photo_item["is_suggestion"] = True
                photo_item["latitude"] = suggestion.latitude
                photo_item["longitude"] = suggestion.longitude
                photo_item["heading"] = suggestion.heading
                photo_item["pitch"] = suggestion.pitch
                photo_item["zoom"] = suggestion.zoom

            memcache.set('photo_%s' % article_id, photo_item, 60 * 10)
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

class AdminHandler(webapp.RequestHandler):
    def get(self):
        if not users.get_current_user() or not users.is_current_user_admin():
            self.response.out.write("<a href='"+users.create_login_url("/admin")+"'>42</a>")
            return
        path = os.path.join(os.path.dirname(__file__), 'static/admin.html')        
        self.response.out.write(open(path, 'r').read())


class AcceptedSuggestionHandler(webapp.RequestHandler):
    def get(self):
        photo_id = self.request.get("photo_id","")
        suggestion_id = self.request.get("suggestion_id","")
        
        accepted = AcceptedSuggestion.get_or_insert(key_name=photo_id)
        accepted.suggestion = db.Key.from_path('Suggestion', int(suggestion_id))
        accepted.put()

class MobileHandler(webapp.RequestHandler):
    def get(self):
        path = os.path.join(os.path.dirname(__file__), 'static/m.html')        
        self.response.out.write(open(path, 'r').read())

class AboutHandler(webapp.RequestHandler):
    def get(self):
        path = os.path.join(os.path.dirname(__file__), 'static/about.html')        
        self.response.out.write(open(path, 'r').read())

class SuggestionHandler(webapp.RequestHandler):
    def post(self):
        latitude = self.request.get('latitude','')
        longitude = self.request.get('longitude','')
        heading = self.request.get('heading','')
        pitch = self.request.get('pitch','')
        zoom = self.request.get('zoom','')
        photo_id = self.request.get('photo_id','')
        
        suggestion = Suggestion()
        suggestion.latitude = float(latitude)
        suggestion.longitude = float(longitude)
        suggestion.heading = float(heading)
        suggestion.pitch = float(pitch)
        suggestion.zoom = float(zoom)
        suggestion.photo_id = int(photo_id)
        suggestion.put()

    def get(self):
        photo_id = self.request.get('photo_id','')
        suggestions = Suggestion.all().filter("photo_id = ",int(photo_id))
        suggestions_json = [{
                'key':s.key().id(),
                'latitude':s.latitude,
                'longitude':s.longitude,
                'heading':s.heading,
                'pitch':s.pitch,
                'zoom':s.zoom,
                'photo_id':s.photo_id} for s in suggestions]
        self.response.headers["Content-Type"] = "application/json"
        self.response.out.write(simplejson.dumps(suggestions_json))        

class Suggestion(db.Model):
    latitude = db.FloatProperty()
    longitude = db.FloatProperty()
    heading = db.FloatProperty()
    pitch = db.FloatProperty()
    zoom = db.FloatProperty()
    photo_id = db.IntegerProperty()

class AcceptedSuggestion(db.Model):
    suggestion = db.ReferenceProperty(Suggestion)

def main():
    application = webapp.WSGIApplication([('/', MainHandler),
                                          ('/about', AboutHandler), 
                                          ('/m', MobileHandler), 
                                          ('/suggestion', SuggestionHandler),
                                          ('/admin',AdminHandler),
                                          ('/accept', AcceptedSuggestionHandler),
                                          ('/list', ListHTML), 
                                          ('/list.json', ListJSON)],
                                         debug=True)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()
