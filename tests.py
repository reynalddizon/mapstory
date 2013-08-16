from django.test import TestCase
from django.test.client import Client
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse

from geonode.maps.models import Layer
from geonode.maps.models import Map
from geonode.maps.models import MapLayer
from geonode.simplesearch import models as simplesearch
from mapstory import social_signals # this just needs activating but is not used
from mapstory import forms
from mapstory.models import Annotation
from mapstory.models import UserActivity
from mapstory.models import ProfileIncomplete
from mapstory.models import audit_layer_metadata
from mapstory.models import Topic
from mapstory.models import Link
from mapstory.templatetags import mapstory_tags
from mapstory.util import unicode_csv_dict_reader

from agon_ratings.models import Rating
from dialogos.models import Comment
from mailer import engine as email_engine

from datetime import timedelta
import json
import logging
import re
import tempfile
import urlparse

# these can just get whacked
simplesearch.map_updated = lambda **kw: None
simplesearch.object_created = lambda **kw: None
Layer.delete_from_geoserver = lambda self: None
Layer._populate_from_gs = lambda s: None
Layer.verify = lambda s: None
Layer.save_to_geoserver = lambda s: None

class SocialTest(TestCase):
    
    fixtures = ['test_data.json','map_data.json']
        
    def setUp(self):
        self.bobby = User.objects.get(username='bobby')
        self.admin = User.objects.get(username='admin')

    def test_social_map_layer_actions(self):
        Layer.objects.create(owner=self.bobby, name='layer1',typename='layer1')
        bobby_layer = Layer.objects.create(owner=self.bobby, name='layer2', typename='layer2')
        # no activity yet, still Private
        self.assertFalse(self.bobby.actor_actions.all())
        
        # lets publish it
        bobby_layer.publish.status = 'Public'
        bobby_layer.publish.save()
        actions = self.bobby.actor_actions.all()
        # there should be a single action
        self.assertEqual(1, len(actions))
        self.assertEqual('bobby published layer2 Layer 0 minutes ago', str(actions[0]))

        # ensure other actions deleted
        self.admin.actor_actions.all().delete()
        # now create a map
        admin_map = Map.objects.create(owner=self.admin, zoom=1, center_x=0, center_y=0, title='map1')
        # have to use a 'dummy' map to create the appropriate JSON
        dummy = Map.objects.get(id=admin_map.id)
        dummy.id += 1
        dummy.save()
        MapLayer.objects.create(name = 'layer1', ows_url='layer1', map=dummy, stack_order=1)
        # and 'add' the layer
        admin_map.update_from_viewer(dummy.viewer_json())
        # no activity yet, still Private
        self.assertFalse(self.admin.actor_actions.all())
        
        # lets publish it and ensure things work
        self.bobby.useractivity.other_actor_actions.clear()
        admin_map.publish.status = 'Public'
        admin_map.publish.save()
        # there should be a single 'public' action (the other exists so it can hang on bobby)
        actions = self.admin.actor_actions.public()
        self.assertEqual(1, len(actions))
        self.assertEqual('admin published map1 by admin 0 minutes ago', str(actions[0]))
        # and a single action for bobby
        actions = self.bobby.useractivity.other_actor_actions.all()
        self.assertEqual(1, len(actions))
        self.assertEqual('admin published layer1 Layer on map1 by admin 0 minutes ago', str(actions[0]))
        
        # already published, add another layer and make sure it shows up in bobby
        self.bobby.useractivity.other_actor_actions.clear()
        MapLayer.objects.create(name = 'layer2', ows_url='layer2', map=dummy, stack_order=2)
        admin_map.update_from_viewer(dummy.viewer_json())
        actions = self.bobby.useractivity.other_actor_actions.all()
        self.assertEqual(1, len(actions))
        self.assertEqual('admin added layer2 Layer on map1 by admin 0 minutes ago', str(actions[0]))

    def test_annotations_filtering(self):
        bobby_layer = Layer.objects.create(owner=self.bobby, name='_map_42_annotations',typename='doesntmatter')
        # lets publish it
        bobby_layer.publish.status = 'Public'
        bobby_layer.publish.save()
        actions = self.bobby.actor_actions.all()
        # no record
        self.assertEqual(0, len(actions))
        bobby_layer.save()
        # no record again
        self.assertEqual(0, len(actions))

    def test_activity_item_tag(self):
        lyr = Layer.objects.create(owner=self.bobby, name='layer1',typename='layer1', title='example')
        lyr.publish.status = 'Public'
        lyr.publish.save()

        comment_on(lyr, self.bobby, 'a comment')
        expected = ("http://localhost:8000/mapstory/storyteller/bobby/ (bobby)"
        " commented on http://localhost:8000/data/layer1 (the StoryLayer 'example')"
        " [ 0 minutes ago ]")
        actual = mapstory_tags.activity_item(self.bobby.actor_actions.all()[0], plain_text=True)
        self.assertEqual(expected, actual)

        rate(lyr, self.bobby, 4)
        expected = ("http://localhost:8000/mapstory/storyteller/bobby/ (bobby)"
        " gave http://localhost:8000/data/layer1 (the StoryLayer 'example')"
        " a rating of 4 [ 0 minutes ago ]")
        actual = mapstory_tags.activity_item(self.bobby.actor_actions.all()[0], plain_text=True)
        self.assertEqual(expected, actual)

        lyr.delete()
        # it seems like comment objects are not deleted when the commented-on object
        # is deleted - test that the tag doesn't blow up
        # @todo is this somehow related to mptt in threaded comments?
        self.assertEqual(1, len(self.bobby.actor_actions.all()))
        for a in self.bobby.actor_actions.all():
            self.assertEqual('', mapstory_tags.activity_item(a))

    def drain_mail_queue(self):
        # mailer doesn't play well with default mail testing
        mails = []
        for m in email_engine.prioritize():
            mails.append(m)
            m.delete()
        return mails
        
    def test_no_notifications(self):
        prefs = UserActivity.objects.get(user=self.bobby)
        prefs.notification_preference = 'N'
        prefs.save()
        
        layer = Layer.objects.create(owner=self.bobby, name='layer1',typename='layer1')
        comment_on(layer, self.admin, "This is great")
        
        prefs.notification_preference = 'E'
        prefs.save()
        comment_on(layer, self.admin, "This is great")
        
        mail = self.drain_mail_queue()
        self.assertEqual(1, len(mail))

    def test_batch_mailer(self):
        prefs = UserActivity.objects.get(user=self.bobby)
        prefs.notification_preference = 'S'
        prefs.save()

        layer = Layer.objects.create(owner=self.bobby, name='layer1',typename='layer1')
        comment_on(layer, self.admin, "This is great")
        comment_on(layer, self.admin, "This is great")

        messages = []
        def handle(self, record):
            messages.append(record)
        handler = type('handler', (logging.Handler,), {'handle':handle})()
        handler.setLevel(logging.INFO)
        logger = logging.getLogger("mapstory.social_signals")
        logger.addHandler(handler)

        social_signals.batch_notification()

        self.assertEqual('2', re.search('\d', messages[0].getMessage()).group())

        action = prefs.other_actor_actions.all()[0]
        action.timestamp = action.timestamp - timedelta(days = 1)
        action.save()

        social_signals.batch_notification()
        self.assertEqual('1', re.search('\d', messages[1].getMessage()).group())

        logger.removeHandler(handler)


def comment_on(obj, user, comment, reply_to=None):
    ct = ContentType.objects.get_for_model(obj)
    return Comment.objects.create(author=user, content_type=ct, object_id=obj.id,
        comment=comment, parent=reply_to)


def rate(obj, user, rating):
    ct = ContentType.objects.get_for_model(obj)
    return Rating.objects.create(user=user, content_type=ct, object_id=obj.id,
        rating=rating)


class LayerAuditTest(TestCase):
    fixtures = ['test_data.json','map_data.json']

    def test_audit(self):
        self.bobby = User.objects.get(username='bobby')
        t = Topic.objects.create(name='xyz')
        layer = Layer.objects.create(owner=self.bobby, name='layer1',typename='layer1')
        self.assertFalse(audit_layer_metadata(layer))
        atts = ('abstract','title','purpose','language','supplemental_information',
                'data_quality_statement')
        for a in atts:
            setattr(layer, a, 'a')
            self.assertFalse(audit_layer_metadata(layer))
        layer.topic_set.add(t)
        self.assertFalse(audit_layer_metadata(layer))
        layer.keywords.add('FOOBARq')
        self.assertFalse(audit_layer_metadata(layer))
        layer.has_thumbnail = lambda : True
        self.assertTrue(audit_layer_metadata(layer))

class LinkTests(TestCase):
    c = Client()

    def test_twitter_link(self):
        link_href = "http://twitter.com/codeforsandiego"
        l = Link(name = "test", href=link_href, order=1)
        self.assertTrue(l.get_twitter_link)

    def test_facebook_link(self):
        link_href = "https://www.facebook.com/hillstreetoside"
        l = Link(name = "test", href=link_href, order=1)
        self.assertTrue(l.get_facebook_link)

class ContactDetailTests(TestCase):

    c = Client()

    def test_incomplete_profile(self):
        u = User.objects.create(username='billy')
        # this will fail if not incomplete, no need for assertions
        ProfileIncomplete.objects.get(user = u)

        # now fill stuff out
        p = u.get_profile()
        u.first_name = 'Billy'
        u.last_name = 'Bob'
        u.save()
        p.update_audit()
        # still incomplete
        ProfileIncomplete.objects.get(user = u)

        p.blurb = 'I Billy Bob'
        p.email = 'billy@b.ob'
        p.save()
        p.update_audit()
        # still incomplete
        ProfileIncomplete.objects.get(user = u)

        # add avatar
        a = u.avatar_set.model(user=u)
        a.save()
        u.avatar_set.add(a)
        p.update_audit()
        # finally
        self.assertEqual(0, ProfileIncomplete.objects.filter(user = u).count())


    def test_profile_form(self):
        email = 'billy@bil.ly'
        u = User.objects.create(username='billy', email=email)
        form = forms.ProfileForm(instance=u.get_profile())
        # email carried over from user
        self.assertEqual(email, form['email'].value())

        # invalid
        form = forms.ProfileForm(data={}, instance=u.get_profile())
        self.assertTrue(not form.is_valid())
        self.assertEqual(['first_name', 'last_name', 'email', 'blurb'], form.errors.keys())

        # first, last, blurb, and email handling all work
        new_email = 'bill@billy.name'
        form = forms.ProfileForm(data={'first_name':'Billy',
                                       'last_name':'Bob',
                                       'blurb':'I Billy Bob',
                                       'email':new_email},
                                 instance=u.get_profile())
        self.assertTrue(form.is_valid())
        form.save()
        # computed name field
        self.assertEqual('Billy Bob', u.get_profile().name)
        # and email applied to both user and profile
        self.assertEqual(new_email, u.email)
        self.assertEqual(new_email, u.get_profile().email)


class AnnotationsTest(TestCase):
    fixtures = ['test_data.json','map_data.json']
    c = Client()

    def setUp(self):
        self.bobby = User.objects.get(username='bobby')
        self.admin = User.objects.get(username='admin')
        admin_map = Map.objects.create(owner=self.admin, zoom=1, center_x=0, center_y=0, title='map1')
        # have to use a 'dummy' map to create the appropriate JSON
        dummy = Map.objects.get(id=admin_map.id)
        dummy.id += 1
        dummy.save()
        self.dummy = dummy

    def make_annotations(self, mapobj, cnt=100):
        for a in xrange(cnt):
            # make sure some geometries are missing
            geom = 'POINT(5 23)' if cnt % 2 == 0 else None
            Annotation.objects.create(title='ann%s' % a, map=mapobj, the_geom=geom).save()

    def test_copy_annotations(self):
        self.make_annotations(self.dummy)

        admin_map = Map.objects.create(owner=self.admin, zoom=1, center_x=0, center_y=0, title='map2')
        # have to use a 'dummy' map to create the appropriate JSON
        target = Map.objects.get(id=admin_map.id)
        target.id += 1
        target.save()

        Annotation.objects.copy_map_annotations(self.dummy.id, target)
        # make sure we have 100 and we can resolve the corresponding copies
        self.assertEqual(100, target.annotation_set.count())
        for a in self.dummy.annotation_set.all():
            self.assertTrue(target.annotation_set.get(title=a.title))

    def test_get(self):
        '''make 100 annotations and get them all as well as paging through'''
        self.make_annotations(self.dummy)

        response = self.c.get(reverse('annotations',args=[self.dummy.id]))
        rows = json.loads(response.content)['features']
        self.assertEqual(100, len(rows))

        for p in range(4):
            response = self.c.get(reverse('annotations',args=[self.dummy.id]) + "?page=%s" % p)
            rows = json.loads(response.content)['features']
            self.assertEqual(25, len(rows))
            # auto-increment id starts with 1
            self.assertEqual(1 + (25 * p), rows[0]['id'])

    def test_post(self):
        '''test post operations'''

        # make 1 and update it
        self.make_annotations(self.dummy, 1)
        ann = Annotation.objects.filter(map=self.dummy)[0]
        data = json.dumps({
            'features' : [{
                'geometry' : {'type' : 'Point', 'coordinates' : [ 5.000000, 23.000000 ]},
                "id" : ann.id,
                'properties' : {
                    "title" : "new title",
                    "start_time" : "2001-01-01",
                    "end_time" : 1371136048
                }
            }]
        })
        # without login, expect failure
        resp = self.c.post(reverse('annotations',args=[self.dummy.id]), data, "application/json")
        self.assertEqual(403, resp.status_code)

        # login and verify change accepted
        self.c.login(username='admin',password='admin')
        resp = self.c.post(reverse('annotations',args=[self.dummy.id]), data, "application/json")
        ann = Annotation.objects.get(id=ann.id)
        self.assertEqual(ann.title, "new title")
        self.assertEqual(ann.the_geom.x, 5)
        self.assertEqual(ann.end_time, 1371136048)
        self.assertEqual(ann.start_time, 978307200)

        # now make a new one with just a title and null stuff
        data = json.dumps({
            'features' : [{
                'properties' : {
                    "title" : "new ann",
                    "geometry" : None
                }
            }]
        })
        resp = self.c.post(reverse('annotations',args=[self.dummy.id]), data, "application/json")
        resp = json.loads(resp.content)
        self.assertEqual(resp['success'], True)
        self.assertEqual([2], resp['ids'])
        ann = Annotation.objects.get(id=ann.id + 1)
        self.assertEqual(ann.title, "new ann")

    def test_delete(self):
        '''test delete operations'''

        # make 10 annotations, drop 4-7
        self.make_annotations(self.dummy, 10)
        data = json.dumps({'action':'delete', 'ids':range(4,8)})
        # verify failure before login
        resp = self.c.post(reverse('annotations',args=[self.dummy.id]), data, "application/json")
        self.assertEqual(403, resp.status_code)

        # now check success
        self.c.login(username='admin',password='admin')
        resp = self.c.post(reverse('annotations',args=[self.dummy.id]), data, "application/json")
        # these are gone
        ann = Annotation.objects.filter(id__in=range(4,8))
        self.assertEqual(0, ann.count())
        # six remain
        ann = Annotation.objects.filter(map=self.dummy)
        self.assertEqual(6, ann.count())

    def test_csv_upload(self):
        '''test csv upload with update and insert'''

        #@todo cleanup and break out into simpler cases

        self.make_annotations(self.dummy, 2)

        header = u"id,title,content,lat,lon,start_time,end_time,appearance\n"

        # first row is insert, second update (as it has an id)
        fp = tempfile.NamedTemporaryFile(delete=True)
        fp.write((
            header +
            u'"",foo bar,blah,5,10,2001/01/01,2005\n'
            u"1,bar foo,halb,10,20,2010-01-01,,\n"
            u"2,bunk,\u201c,20,30,,,"
        ).encode('utf-8'))
        fp.seek(0)
        # verify failure before login
        resp = self.c.post(reverse('annotations',args=[self.dummy.id]),{'csv':fp})
        self.assertEqual(403, resp.status_code)
        # still only 2 annotations
        self.assertEqual(2, Annotation.objects.filter(map=self.dummy.id).count())

        # login, rewind the buffer and verify
        self.c.login(username='admin',password='admin')
        fp.seek(0)
        resp = self.c.post(reverse('annotations',args=[self.dummy.id]),{'csv':fp})
        # response type must be text/html for ext fileupload
        self.assertEqual('text/html', resp['content-type'])
        jsresp = json.loads(resp.content)
        self.assertEqual(True, jsresp['success'])
        ann = Annotation.objects.filter(map=self.dummy.id)
        # we uploaded 3, the other 2 should be deleted (overwrite mode)
        self.assertEqual(3, ann.count())
        ann = Annotation.objects.get(title='bar foo')
        self.assertEqual(ann.the_geom.x, 20.)
        ann = Annotation.objects.get(title='bunk')
        self.assertTrue(u'\u201c', ann.content)
        ann = Annotation.objects.get(title='foo bar')
        self.assertEqual('foo bar', ann.title)
        self.assertEqual(ann.the_geom.x, 10.)

        resp = self.c.get(reverse('annotations',args=[self.dummy.id]) + "?csv")
        x = list(unicode_csv_dict_reader(resp.content))
        self.assertEqual(3, len(x))
        by_title = dict( [(v['title'],v) for v in x] )
        # verify round trip of unicode quote
        self.assertEqual(u'\u201c', by_title['bunk']['content'])
        # and times
        self.assertEqual('2010-01-01T00:00:00', by_title['bar foo']['start_time'])
        self.assertEqual('2001-01-01T00:00:00', by_title['foo bar']['start_time'])
        self.assertEqual('2005-01-01T00:00:00', by_title['foo bar']['end_time'])

        # verify windows codepage quotes
        fp = tempfile.NamedTemporaryFile(delete=True)
        fp.write((
            str(header) +
            ',\x93windows quotes\x94,yay,,,,'
        ))
        fp.seek(0)
        resp = self.c.post(reverse('annotations',args=[self.dummy.id]),{'csv':fp})
        ann = Annotation.objects.get(map=self.dummy.id)
        # windows quotes are unicode now
        self.assertEqual(u'\u201cwindows quotes\u201d', ann.title)

        # make sure a bad upload aborts the transaction (and prevents dropping existing)
        fp = tempfile.NamedTemporaryFile(delete=True)
        fp.write((
            str(header) * 2
        ))
        fp.seek(0)
        resp = self.c.post(reverse('annotations',args=[self.dummy.id]),{'csv':fp})
        self.assertEqual(400, resp.status_code)
        # there should only be one that we uploaded before
        Annotation.objects.get(map=self.dummy.id)
        self.assertEqual('yay', ann.content)
        # @todo verify error messages
        

class UtilTest(TestCase):

    def test_unicode_csv_dict_reader(self):
        #@todo cleanup
        fp = tempfile.NamedTemporaryFile(delete=True)
        fp.write((
            'abc,xyz\n' +
            # \x9d is some control char - will be ignored??
            'blah\x9d,\x93windows quotes\x94\n'
        ))
        fp.seek(0)
        rows = list(unicode_csv_dict_reader(fp))
        # cp1252 quotes get translated to unicode
        self.assertEqual(u'\u201cwindows quotes\u201d', rows[0]['xyz'])
        fp = tempfile.NamedTemporaryFile(delete=True)
        fp.write((
            u'abc,xyz\n' +
            u'blah,\u201cunicode quotes\u201d\n'
        ).encode('utf-8'))
        fp.seek(0)
        rows = list(unicode_csv_dict_reader(fp))
        self.assertEqual(u'\u201cunicode quotes\u201d', rows[0]['xyz'])


class LinkTest(TestCase):

    def test_tags(self):
        url = mapstory_tags.ext_url('wiki', 'curation_guide_ratings')
        self.assertEqual("http://wiki.mapstory.org/index.php?title=Curation_Guide#Ratings", url)
        link = mapstory_tags.ext_link('wiki', 'curation_guide_ratings')
        self.assertEqual('<a href="http://wiki.mapstory.org/index.php?title=Curation_Guide#Ratings"></a>',
            link)
        link = mapstory_tags.ext_link('wiki', 'curation_guide_ratings',
            classes='blah')
        self.assertEqual('<a href="http://wiki.mapstory.org/index.php?title=Curation_Guide#Ratings" class="blah"></a>', link)

    def test_verify_links(self):
        from mapstory.links import links
        passed, failed = self._verify_links(links)
        if failed:
            self.fail('\n'.join(failed))
        # make sure we checked something
        self.assertTrue(len(passed) > 0)
        
    def test_verify(self):
        '''make sure test works with bad data'''
        links = {
            "bunk" : {
                "links" : {
                    'bad' : 'http://wiki.mapstory.org/blah',
                    'missing_fragment' : "http://wiki.mapstory.org/index.php?title=Curation_Guide#MISSING"
                }
            }
        }
        passed, failed = self._verify_links(links)
        self.assertTrue(len(passed), 0)
        expected = [
            ('bad', 'http://wiki.mapstory.org/blah', 'invalid response: 404'),
            ('missing_fragment', 'http://wiki.mapstory.org/index.php?title=Curation_Guide#MISSING', 'could not locate fragment: MISSING')
        ]
        self.assertEqual(expected, failed)

    def _verify_links(self, links):
        from bs4 import BeautifulSoup
        import httplib2
        http = httplib2.Http()
        failed = []
        passed = []
        for cat in links.values():
            hashed = cat['links']
            cached = {}
            for name, url in hashed.items():
                cache_key = re.sub('#.*','',url)
                if cache_key not in cached:
                    print 'fetching content from %s' % url
                    resp, content = http.request(url, 'GET')
                    if resp.status != 200:
                        failed.append((name, url, 'invalid response: %s' % resp.status))
                        continue
                    cached[cache_key] = resp, content
                else:
                    resp, content = cached[cache_key]
                parts = urlparse.urlparse(url)
                if parts.fragment:
                    if not isinstance(content, BeautifulSoup):
                        content = BeautifulSoup(content)
                        cached[cache_key] = resp, content
                    found = content.select('#%s' % parts.fragment)
                    if len(found) == 0:
                        failed.append((name, url, 'could not locate fragment: %s' % parts.fragment))
                passed.append(name)
        return passed, failed
