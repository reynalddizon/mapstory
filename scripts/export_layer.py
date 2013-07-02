'''Extract a layer and relevant resources'''
from django.core import serializers
from django.conf import settings

from geonode.maps.models import Layer

from mapstory.models import PublishingStatus

import json
import psycopg2
import sys
import os
import tempfile
import shutil
from xml.etree.ElementTree import tostring


def export_layer(conn, tempdir, layer):
    gslayer = Layer.objects.gs_catalog.get_layer(layer.typename)
    gsresource = gslayer.resource

    # fetch the nativeName, the name of the table in the database
    # which is not necessarily the same name as the layer
    gsresource.fetch()
    nativeName = gsresource.dom.find('nativeName').text

    temppath = lambda *p: os.path.join(tempdir, *p)

    cursor = conn.cursor()

    #dump db table - this gets the table schema, too
    dump_cmd = 'pg_dump -f %s --format=c --create --table=\\"%s\\" --username=%s %s' % (
        os.path.join(tempdir, 'layer.dump'), nativeName, settings.DB_DATASTORE_USER, settings.DB_DATASTORE_DATABASE)
    retval = os.system(dump_cmd)
    if retval != 0:
        print dump_cmd
        print 'failed!'
        sys.exit(1)

    #get the geometry_columns entry
    cursor.execute("select * from geometry_columns where f_table_name='%s'" % nativeName)
    with open(temppath('geom.info'),'wb') as fp:
        fp.write(str(cursor.fetchall()))
    
    #dump django Layer object
    with open(temppath('model.json'),'wb') as fp:
        fp.write(serializers.serialize("json", [layer]))

    #copy geoserver layer info
    workspace_path = 'workspaces/%s/%s/%s' % (gsresource.workspace.name, gsresource.store.name, layer.name)
    os.makedirs(temppath(workspace_path))
    open(temppath(workspace_path, 'featuretype.xml'), 'w').write(tostring(gsresource.dom))
    open(temppath(workspace_path, 'layer.xml'), 'w').write(tostring(layer.publishing.dom))

    #gather styles
    os.makedirs(temppath('styles'))
    def copy_style(style):
        if not style: return
        style.fetch()
        sld_filename = temppath('styles', style.filename)
        open(sld_filename, 'w').write(style.sld_body)

    copy_style(gslayer.default_style)
    map(copy_style, gslayer.styles)

    # dump out thumb_spec if exists
    t = layer.get_thumbnail()
    if t:
        with open(temppath('thumb_spec.json'), 'w') as f:
            json.dump(t.thumb_spec, f)
    
    try:
        pubstat = PublishingStatus.objects.get(layer=layer)
        with open(temppath('publishingstatus.json'), 'w') as f:
            serializers.serialize('json', [pubstat], stream=f)
    except PublishingStatus.DoesNotExist:
        print 'No publishing status found for layer: %s' % layer

    cursor.close()

if __name__ == '__main__':

    args = sys.argv[1:]
    if not args:
        print 'use: extract_layer.py layername'
        sys.exit(1)
    
    conn = psycopg2.connect("dbname='" + settings.DB_DATASTORE_DATABASE + 
                            "' user='" + settings.DB_DATASTORE_USER + 
                            "' password='" + settings.DB_DATASTORE_PASSWORD + 
                            "' port=" + settings.DB_DATASTORE_PORT + 
                            " host='" + settings.DB_DATASTORE_HOST + "'")

    layer_name = args.pop()
    try:
        layer = Layer.objects.get(name=layer_name)
    except Layer.DoesNotExist:
        print 'no such layer'
        sys.exit(1)

    tempdir = tempfile.mkdtemp()

    # creates the layer layout structure in the temp directory
    export_layer(conn, tempdir, layer)

    # zip files
    curdir = os.getcwd()
    os.chdir(tempdir)
    os.system('zip -r %s/%s-extract.zip .' % (curdir,layer_name))

    # and cleanup
    shutil.rmtree(tempdir)
    conn.close()
