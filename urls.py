from django.conf.urls.defaults import *
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core import urlresolvers
from django.http import HttpResponse
from django.shortcuts import redirect
from django.views.generic.simple import direct_to_template
from django.views.generic import RedirectView
from geonode.sitemap import LayerSitemap, MapSitemap
from geonode.proxy.urls import urlpatterns as proxy_urlpatterns
from mapstory.forms import ProfileForm
from mapstory.views import SignupView
from hitcount.views import update_hit_count_ajax
from account.views import ConfirmEmailView
from account.views import LoginView
from account.views import LogoutView

import hmac
import hashlib

# load our social signals
from mapstory import social_signals

from django.contrib import admin
admin.autodiscover()

import oembed
oembed.autodiscover()
from oembed_providers import MapStoryProvider
oembed.site.register(MapStoryProvider)

js_info_dict = {
    'domain': 'djangojs',
    'packages': ('geonode',)
}

sitemaps = {
    "layer": LayerSitemap,
    "map": MapSitemap
}


# hack login/logout to set cookies for the warper
# this will only work if the site is running on mapstory.org
class WarperCookieLogin(LoginView):
    def post(self, *args, **kwargs):
        super(WarperCookieLogin, self).post(*args, **kwargs)
        if self.request.user.is_authenticated():
            return HttpResponse(status=200)
        return HttpResponse(
                    content="invalid login",
                    status=400,
                    mimetype="text/plain"
                )

    def form_valid(self, form):
        resp = super(WarperCookieLogin, self).form_valid(form)
        key = getattr(settings, 'WARPER_KEY', 'abc123')
        digested = hmac.new(key, form.user.username, hashlib.sha1).hexdigest()
        cookie = '%s:%s' % (form.user.username, digested)
        resp.set_cookie('msid', cookie, domain='warper.mapstory.org', httponly=True)
        return resp


class WarperCookieLogout(LogoutView):
    def post(self, *args, **kwargs):
        resp = super(WarperCookieLogout, self).post(self, *args, **kwargs)
        resp.delete_cookie('msid', domain='warper.mapstory.org')
        return resp


class NamedRedirect(RedirectView):
    name = None
    permanent = False
    not_post = False
    '''this will only work for no-args reverses'''
    def get_redirect_url(self, **kwargs):
        if not self.url:
            self.url = urlresolvers.reverse(self.name)
        return RedirectView.get_redirect_url(self, **kwargs)
    def post(self, req, *args, **kw):
        # @ugh - the /maps/ endpoint is used one way for get, another for post
        # we want post to pass through to the original...
        if self.not_post:
            match =  urlresolvers.get_resolver('geonode.urls').resolve(req.path)
            return match.func(req, *args, **kw)
        else:
            return RedirectView.post(self, req, *args, **kw)


urlpatterns = patterns('',
    # inject our form into these views
    ('^profiles/edit/$', 'profiles.views.edit_profile', {'form_class': ProfileForm,}),
    ('^profiles/create/$', 'profiles.views.create_profile', {'form_class': ProfileForm,}),
    # and redirect the profile list
    url('^profiles/$', NamedRedirect.as_view(name='search_owners')),

    # alias these for compat with security from geonode2
    url('^layers/acls$', 'geonode.maps.views.layer_acls'),
    url('^layers/resolve_user$', 'geonode.maps.views.user_name'),

)

urlpatterns += patterns('mapstory.views',
    (r'^(?:index/?)?$', 'index'),

    # ugh, overrides
    # for the account views - we are only using these
    url(r"^accounts/ajax_login", WarperCookieLogin.as_view(), name="account_login"),
    url(r"^accounts/logout", WarperCookieLogout.as_view(), name="account_logout"),
    url(r"^account/confirm_email/(?P<key>\w+)/$", ConfirmEmailView.as_view(), name="account_confirm_email"),
    url(r"^account/signup/$", SignupView.as_view(), name="account_signup"),
    # and this from geonode
    url(r'^data/(?P<layername>[^/]*)/metadata$', 'layer_metadata', name="layer_metadata"),
    # and to make url kinda sane
    url(r'^profiles/edit/links$', 'user_links', name='user_links'),
    url(r'^profiles/edit/ribbon$', 'user_links', {'link_type' : 'ribbon_links'}, name='user_ribbon_links'),
    
    # redirect some common geonode stuff
    url(r'^data/$', NamedRedirect.as_view(name='search_layers'), name='data_home'),
    url(r'^maps/$', NamedRedirect.as_view(name='search_maps', not_post=True), name='maps_home'),
    # and allow missing slash for uploads
    url(r'^data/upload$', NamedRedirect.as_view(name='data_upload')),
    # don't use the old registration page
    url(r'^accounts/register/$', RedirectView.as_view(url='/account/signup/'), name='registration_register'),

    (r'^admin/reports/', include('mapstory.reports.urls')),

    (r'', include('geonode.simplesearch.urls')), # put this first to ensure search urls priority
    (r'', include('geonode.urls')),

    url(r"^invites/", include("kaleo.urls")),
    url(r'^oembed/', include("oembed.urls")),

    (r'^data/create_annotations_layer/(?P<mapid>\d+)$','create_annotations_layer'),
    url(r'^mapstory/donate/$',direct_to_template, {"template":"mapstory/donate.html"},name='donate'),
    url(r'^mapstory/thanks/$',direct_to_template, {"template":"mapstory/thanks.html"}),
    url(r'^mapstory/invites/$',login_required(direct_to_template), {"template":"mapstory/invites.html"}, name='invites_page'),
    url(r'^mapstory/invites/preview$', 'invite_preview', name='invite_preview'),
    url(r'^mapstory/alerts/$','alerts',name='alerts'),
    url(r'^mapstory/tile/(?P<mapid>\d+)$','map_tile',name='map_tile'),
    url(r'^mapstory/tiles$','map_tiles',name='map_tiles'),
    url(r'^mapstory/storyteller/(?P<username>\S+)/$','about_storyteller',name='about_storyteller'),
    url(r'^mapstory/storyteller/(?P<username>\S+)/actions$','storyteller_activity_pager',name='storyteller_activity_pager'),
    url(r'^mapstory/storyteller/(?P<username>\S+)/other-actions$','storyteller_activity_pager', {'what':'other'}, name='storyteller_other_activity_pager'),
    url(r'^mapstory/section/(?P<section>[-\w]+)/$','section_detail',name='section_detail'),
    url(r'^mapstory/section/(?P<section>[-\w]+)/tiles$','section_tiles',name='section_tiles'),
    url(r'^mapstory/resource/(?P<resource>[-\w]+)/$','resource_detail',name='mapstory_resource'),
    url(r'^mapstory/how-to/$','how_to',name='how_to'),
    url(r'^mapstory/reflections/$','reflections',name='reflections'),
    url(r'^mapstory/manual/$','manual',name='mapstory_manual'),
    url(r'^mapstory/admin-manual/$','admin_manual',name='mapstory_admin_manual'),
    url(r'^mapstory/by_storyteller_pager/(?P<user>\S+)/(?P<what>\S+)$','by_storyteller_pager',name='by_storyteller_pager'),
    url(r'^mapstory/related_mapstories_pager/(?P<map_id>\d+)$','related_mapstories_pager',name='related_mapstories_pager'),
    url(r'^data/style/upload$','upload_style',name='upload_style'),

    # semi-temp urls
    url(r'^mapstory/user_activity_api$','user_activity_api',name='user_activity_api'),
    url(r'^mapstory/metadata/(?P<layer_id>\d+)$','layer_xml_metadata',name='layer_xml_metadata'),
    url(r'^mapstory/topics/(?P<layer_or_map>\w+)/(?P<layer_or_map_id>\d+)$','topics_api',name='topics_api'),
    url(r'^mapstory/comment/(?P<layer_or_map_id>\d+)/(?P<comment_id>\d+)$','delete_story_comment',name='delete_story_comment'),
    url(r'^mapstory/flag_comment$','flag_comment',name='flag_comment'),
    url(r'^favorite/map/(?P<id>\d+)$','favorite',{'subject':'map'}, name='add_favorite_map'),
    url(r'^favorite/layer/(?P<id>\d+)$','favorite',{'subject':'layer'}, name='add_favorite_layer'),
    url(r'^favorite/user/(?P<id>\d+)$','favorite',{'subject':'user'}, name='add_favorite_user'),
    url(r'^favorite/(?P<id>\d+)/delete$','delete_favorite',name='delete_favorite'),
    url(r'^mapstory/publish/(?P<layer_or_map>\w+)/(?P<layer_or_map_id>\d+)$','publish_status',name='publish_status'),
    url(r'^mapstory/add-to-map/(?P<id>\d+)/(?P<typename>[:\w]+)','add_to_map',name='add_to_map'),
    url(r'^search/favoriteslinks$','favoriteslinks',name='favoriteslinks'),
    url(r'^search/favoriteslist$','favoriteslist',name='favoriteslist'),
    url(r'^mapstory/resource/(?P<resource>[-\w]+)/links', 'resource_links', name='resource_links'),
    url(r'^mapstory/resource/(?P<resource>[-\w]+)/ribbon', 'resource_links', {'link_type' : 'ribbon_links'}, name='resource_ribbon_links'),
    url(r'^maps/(?P<mapid>\d+)/annotations$','annotations',name='annotations'),

    url(r'^ajax/hitcount/$', update_hit_count_ajax, name='hitcount_update_ajax'),

    url(r"^announcements/", include("announcements.urls")),
    url(r"^flag/", include("flag.urls")),

    # for now, direct-to-template but should be in database
    url(r"^mapstory/thoughts/jonathan-marino/$", direct_to_template, {"template": "mapstory/thoughts.html",
        "extra_context" : {'html':'mapstory/thoughts/jm.html'}}, name="thoughts-jm"),
    url(r"^mapstory/thoughts/parag-khanna/$", direct_to_template, {"template": "mapstory/thoughts.html",
        "extra_context" : {'html':'mapstory/thoughts/pk.html'}}, name="thoughts-pk"),
    url(r"^mapstory/thoughts/roberta-balstad/$", direct_to_template, {"template": "mapstory/thoughts.html",
        "extra_context" : {'html':'mapstory/thoughts/rb.html'}}, name="thoughts-rb"),
    url(r"^mapstory/thoughts/r-siva-kumar/$", direct_to_template, {"template": "mapstory/thoughts.html",
        "extra_context" : {'html':'mapstory/thoughts/sk.html'}}, name="thoughts-sk"),
    url(r"^mapstory/thoughts/robert-tomes/$", direct_to_template, {"template": "mapstory/thoughts.html",
        "extra_context" : {'html':'mapstory/thoughts/rt.html'}}, name="thoughts-rt"),
    url(r"^mapstory/thoughts/jamie-gahlon/$", direct_to_template, {"template": "mapstory/thoughts.html",
        "extra_context" : {'html':'mapstory/thoughts/jg.html'}}, name="thoughts-jg"),
    url(r"^mapstory/thoughts/jen-ziemke/$", direct_to_template, {"template": "mapstory/thoughts.html",
        "extra_context" : {'html':'mapstory/thoughts/jz.html'}}, name="thoughts-jz"),
    
    # the catchall
    url(r'^(?P<org_slug>[-\w]+)/$', 'org_page', name='org_page'),
    url(r'^(?P<org_slug>[-\w]+)/api$', 'org_page_api', name='org_page_api'),
    url(r'^(?P<org_slug>[-\w]+)/ribbon$', 'org_links', {'link_type' : 'ribbon_links'}, name='org_ribbon_links'),
    url(r'^(?P<org_slug>[-\w]+)/links$', 'org_links', name='org_links'),
)

urlpatterns += proxy_urlpatterns

if settings.ENABLE_SOCIAL_LOGIN:
    urlpatterns += patterns('',
        url(r'', include('social_auth.urls')),
        url(r'^oauth2/', include('provider.oauth2.urls', namespace = 'oauth2')),
    )

# Extra static file endpoint for development use
if settings.SERVE_MEDIA:
    urlpatterns += patterns('',
        url(r'^media/(?P<path>.*)$', 'django.views.static.serve', {
            'document_root': settings.MEDIA_ROOT,
        }),
        # this is here to allow testing staticfiles, don't remove (ian)
        url(r'^static/(?P<path>.*)$','django.views.static.serve',{
            'document_root' : settings.STATIC_ROOT,
        }),
        url(r'^thumbs/(?P<path>.*)$','django.views.static.serve',{
            'document_root' : settings.THUMBNAIL_STORAGE,
        })
    )
