import os.path
# support for client config migrations
#
#
#
import json
import optparse # for 2.6 support
import os
import sys

os.environ['DJANGO_SETTINGS_MODULE'] = "mapstory.settings"
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from django.db import transaction
from django.core import serializers
from django.conf import settings
from geonode.maps.models import MapLayer
from geonode.maps.models import Map


class MigrationException(Exception):
    pass


class ConfigMigration(object):

    query_set = None

    dry_run = True

    def do_backup(self):
        'dump serialized models before changing them'
        if self.query_set is None:
            raise Exception('need a query_set defined')
        backup_name = '%s_backup.json' % self.__class__.__name__
        if not self.opts.force_backup and os.path.exists(backup_name):
            raise MigrationException('backup file exists, please delete or provide -f option : %s' % backup_name)
        if self.query_set.count():
            data = serializers.serialize("json", self.query_set)
            with open(backup_name, 'w') as fp:
                fp.write(data)
            print 'backed up %s models to %s' % (self.query_set.count(), backup_name)
            
    def _get_backup(self):
        backup_name = '%s_backup.json' % self.__class__.__name__
        if not os.path.exists(backup_name):
            raise MigrationException('no backup present')
        return serializers.deserialize("json", open(backup_name).read())

    def restore(self):
        'restore from serialized models'
        if self.dry_run:
            print 'DRY RUN!'
        filters = [ f.split('=') for f in self.opts.filter ] if self.opts.filter else None
        def get_rule(obj):
            if filters:
                stuff = dir(obj)
                for f in filters:
                    if not f[0] in stuff:
                        print 'filter attr invalid, possible values are', stuff
                return lambda o: all([ str(getattr(o,f[0])) == f[1] for f in filters])
            else:
                return lambda o: True
        applies = None
        for obj in self._get_backup():
            applies = applies if applies else get_rule(obj.object)
            if applies(obj.object):
                print 'restoring', obj.object
                if not self.dry_run:
                    obj.save()

    def _configure(self, opts, args):
        'do general config'
        self.dry_run = not opts.run
        self.opts = opts
        self.args = args

    def configure(self, opts, args):
        'override for specific config'
        pass

    def init(self):
        'if query_set must be more dynamic, etc'
        pass

    def _run(self):
        'general run'
        self.init()
        if self.opts.filter:
            for e in self.opts.filter:
                k,v = e.split('=')
                self.query_set = self.query_set.filter(**{k:v})
        if self.dry_run:
            msg = 'dry run, will not make any changes'
            print '*' * len(msg)
            print msg
            print '*' * len(msg)
        if not self.dry_run:
            self.do_backup()
        transaction.enter_transaction_management()
        transaction.managed(True)
        try:
            self.run()
        except:
            print 'aborting transaction'
            transaction.rollback()
            raise
        else:
            transaction.commit()


    def process_model(self, m):
        raise Exception('implement process_model')

    def run(self):
        'override me or process_model'
        print 'processing %s models' % self.query_set.count()
        for m in self.query_set:
            self.process_model(m)
            if not self.dry_run:
                m.save()

    def configure_options(self, parser):
        pass

    def main(self, options, args):
        self._configure(options, args)
        self.configure(options, args)
        if options.restore:
            self.restore()
        else:
            self._run()


class BaseLayerNameMigration(ConfigMigration):
    'migrate base layer names'

    name_mappings = {
        'Wayne': 'Naked Earth',
        'bluemarble': 'Satellite Imagery'
    }

    def init(self):
        self.query_set = MapLayer.objects.filter(name__in=self.name_mappings.keys())

    def process_model(self, m):
        new_name = self.name_mappings[m.name]
        print 'updating %s to %s, in map: %s' % (m.name, new_name, m.map.id)
        layer_params = json.loads(m.layer_params)
        layer_params['title'] = new_name
        layer_params['args'][0] = new_name
        m.layer_params = json.dumps(layer_params)
        m.name = new_name


class RemoveMapProperties(ConfigMigration):
    'remove any gxp_mapproperties tools from stored map configuration'

    query_set = Map.objects.filter(tools_params__contains='gxp_mapproperties')

    def process_model(self, m):
        if not m.tools_params:
            return
        tools_params = json.loads(m.tools_params)
        filtered = [ t for t in tools_params if not t['ptype'] == 'gxp_mapproperties']
        if filtered != tools_params:
            print 'will remove tools from', m.title, m.id
        m.tools_params = json.dumps(filtered)


class UseVirtualOWSURL(ConfigMigration):
    'update ows_url to point to virtual service'

    query_set = MapLayer.objects.exclude(ows_url__startswith='http').exclude(ows_url__isnull=True) 

    def process_model(self, m):
        print 'processing %s, map=%s' % (m.name, m.map.id)
        if m.name.find('geonode:') == 0:
            print 'updating name to remove prefix'
            m.name = m.name.replace('geonode:', '')
            m.ows_url = '%sgeonode/%s/wms' % (settings.GEOSERVER_BASE_URL, m.name)
            print 'updating ows_url=%s' % m.ows_url
        config = json.loads(m.source_params)
        config['id'] = 'geonode:%s-search' % m.name
        print 'updating source_params.id to %s' % config['id']
        m.source_params = json.dumps(config)
        config = json.loads(m.layer_params)
        if 'capability' in config:
            config['capability']['prefix'] = m.name
            config['capability']['name'] = m.name
            print 'adjusted capability name and prefix to %s' % m.name
            m.layer_params = json.dumps(config)


def _migrations():
    migrations = []
    for v in globals().items():
        try:
            if v[1] != ConfigMigration and issubclass(v[1], ConfigMigration):
                migrations.append(v)
        except TypeError:
            pass
    return migrations


def _print_help(parser, exit=0):
    parser.print_help()
    print
    print 'available migrations:'
    print '\t','\n\t'.join( ['%s - %s' % (v[0],v[1].__doc__) for v in _migrations()])
    sys.exit(exit)


if __name__ == '__main__':
    parser = optparse.OptionParser("usage: %prog [help] [options] migration")
    parser.add_option('-r', '--run',
        help='Unless specified, will only print what would happen',
        action='store_true', default=False)
    parser.add_option('-l', '--restore',
        help='Restore model dump',
        action='store_true', default=False)
    parser.add_option('-f', '--force-backup',
        help='Overwrite any existing backup',
        action='store_true', default=False)
    parser.add_option('-i', '--filter',
        help='Limit the query further with provided keywords, ex. map__id=22 ',
        action='append')

    args = sys.argv[1:]
    if not len(args):
        _print_help(parser)
    help = 'help' in args
    if help:
        args.remove('help')
        if not len(args):
            print 'help requires a migration name'
            sys.exit(1)
    migrations = dict([ (v[0].lower(),v[1]) for v in _migrations() ])
    migration_name = [ a for a in args if a[0] != '-' ]
    migration_name = migration_name[0] if migration_name else None
    if not migration_name:
        _print_help(parser, 1)
    if not migration_name.lower() in migrations:
        print 'migration not found:', migration_name
        _print_help(parser, 1)
    migration = migrations[migration_name.lower()]()
    migration.configure_options(parser)
    if help: _print_help(parser)
    try:
        migration.main(*parser.parse_args(args))
    except MigrationException, me:
        print me
