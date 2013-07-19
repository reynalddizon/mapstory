import psycopg2
from django.conf import settings

def open_db_datastore_connection():
    params = [
        ('dbname', 'DB_DATASTORE_DATABASE'),
        ('user', 'DB_DATASTORE_USER'),
        ('password', 'DB_DATASTORE_PASSWORD'),
        ('port', 'DB_DATASTORE_PORT'),
        ('host', 'DB_DATASTORE_HOST'),
    ]
    return psycopg2.connect(' '.join([ "%s='%s'" % (k,getattr(settings,v)) for k,v in params ]))
