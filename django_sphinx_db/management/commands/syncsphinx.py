import inspect
from optparse import make_option
from django.db.models import fields
from django.db.models.fields import related
from django.conf import settings
from django.utils.importlib import import_module
from django.core.management.base import BaseCommand
from django_sphinx_db.backend.models import SphinxModel, SphinxField


CONF_TEMPLATE = '''\

#*~ Auto-generated by django-sphinx-db ~*
index %(index_name)s
{
	# Options:
	type			= rt
	path			= %(directory)s/%(index_name)s
	enable_star		= 1

	# Fields:
	%(fields)s
} #*~ End auto-generation ~*
'''
CONF_FIELD_TEMPLATE = '%(field_type)s%(indent)s= %(field_name)s'

FIELD_TYPE_MAP = {
    # By no means exhaustive list of Sphinx types to Django field types.
    'rt_field': (
        SphinxField,
    ),
    'rt_attr_timestamp': (
        fields.TimeField,
        fields.DateField,
        fields.DateTimeField,
    ),
    'rt_attr_uint': (
        fields.SmallIntegerField,
        fields.IntegerField,
        related.ForeignKey,
    ),
    'rt_attr_string': (
        fields.CharField,
        fields.EmailField,
    ),
    'rt_attr_float': (
        fields.DecimalField,
        fields.FloatField,
    ),
    'rt_attr_bigint': (
        fields.BigIntegerField,
    ),
}


def iter_models():
    for app in settings.INSTALLED_APPS:
        try:
            models = import_module('.models', app)
        except ImportError:
            continue
        for attr in dir(models):
            model = getattr(models, attr)
            if inspect.isclass(model) and \
               issubclass(model, SphinxModel) and \
               model != SphinxModel:
                yield model


def iter_fields(model):
    for i, field in enumerate(model._meta.fields):
        if i == model._meta.pk_index():
            # Don't include the id field in configuration, it is implied.
            continue
        yield field.name, field


class Command(BaseCommand):
    args = ''
    help = 'Builds a configuration for Sphinx from your Django models.'
    option_list = BaseCommand.option_list + (
        make_option(
            '--directory',
            default = '/var/indexes',
            help = 'Data directory for index data files.',
        ),
    )

    def handle(self, *args, **kwargs):
        field_types = {}
        for model in iter_models():
            for name, field in iter_fields(model):
                for type, klasses in FIELD_TYPE_MAP.items():
                    if any(map(lambda klass: isinstance(field, klass), klasses)):
                        field_types[name] = type
                        break
            field_conf = []
            for field_name, field_type in field_types.items():
                field_conf.append(CONF_FIELD_TEMPLATE % dict(
                    field_name = field_name,
                    indent = '\t' * (3 - len(field_type) / 8),
                    field_type = field_type
                ))
            print CONF_TEMPLATE % dict(
                fields = '\n\t'.join(field_conf),
                index_name = model._meta.db_table,
                directory = kwargs.get('directory')
            )
