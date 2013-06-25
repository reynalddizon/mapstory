from mapstory.models import *
from django import forms
from django.contrib.contenttypes.models import ContentType
from django.contrib import admin
from django.http import HttpResponseRedirect
from django.http import HttpResponse
from django.core.urlresolvers import reverse
from django.contrib.auth.admin import UserAdmin
import csv

from mapstory.reports.admin import export_via_model


def export_as_csv_action(description="Export selected objects as CSV file",
                         fields=None, exclude=None, query_factory=None):
    """
    This function returns an export csv action
    'fields' and 'exclude' work like in django ModelForm
    'header' is whether or not to output the column names as the first row
    """
    def export_as_csv(modeladmin, request, queryset):
        """
        Generic csv export admin action.
        based on http://djangosnippets.org/snippets/1697/

        queryset is an iterable returning an object
        with attributes or no-arg callables matching the field names
        """
        if query_factory:
            queryset = query_factory(queryset)

        return export_via_model(
            modeladmin.model,
            request,
            queryset,
            fields,
            exclude
        )

    export_as_csv.short_description = description
    return export_as_csv


# remove non important values form the export script
export_func = export_as_csv_action(
    exclude=[
        'password',
        'is_active',
        'is_superuser',
        'id'
    ]
)
UserAdmin.actions = [export_func]


class ResourceForm(forms.ModelForm):
    text = forms.CharField(widget=forms.Textarea)
    class Meta:
        model = Resource

class ResourceAdmin(admin.ModelAdmin):
    list_display = 'id','name','order'
    list_display_links = 'id',
    list_editable = 'name','order'
    form = ResourceForm
    ordering = ['order',]

class SectionForm(forms.ModelForm):
    text = forms.CharField(widget=forms.Textarea)
    class Meta:
        model = Section

class SectionAdmin(admin.ModelAdmin):
    list_display = 'id','name','order'
    list_display_links = 'id',
    list_editable = 'name','order'
    form = SectionForm
    ordering = ['order',]


class LinkAdmin(admin.ModelAdmin):
    list_display = 'id','name','href','order','render'
    list_display_links = 'id',
    list_editable = 'name','href','order'


class VideoLinkForm(forms.ModelForm):
    text = forms.CharField(widget=forms.Textarea)
    class Meta:
        model = VideoLink

class VideoLinkAdmin(admin.ModelAdmin):
    list_display = 'id','name','title','href','publish','location'
    list_display_links = 'id',
    list_editable = 'name','title','publish','href','location'
    form = VideoLinkForm

class ContactDetailAdmin(admin.ModelAdmin):
    pass

class OrgAdmin(admin.ModelAdmin):
    exclude = ('links','ribbon_links')
    def get_form(self, request, obj=None, **kwargs):
        if not obj:
            self.fields = ('organization',)
        else:
            self.fields = None
        return super(OrgAdmin, self).get_form(request, obj, **kwargs)

class OrgContentAdmin(admin.ModelAdmin):
    pass

#@hack the UserAdmin to enable sorting by date_joined
UserAdmin.list_display += ('date_joined',)

admin.site.register(VideoLink, VideoLinkAdmin)
admin.site.register(Section, SectionAdmin)
admin.site.register(ContactDetail, ContactDetailAdmin)
admin.site.register(Resource, ResourceAdmin)
admin.site.register(Org, OrgAdmin)
admin.site.register(OrgContent, OrgContentAdmin)
admin.site.register(Topic)
admin.site.register(Link, LinkAdmin)
