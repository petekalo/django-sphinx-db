from django.db import models
from django.db.models.sql import Query
from django.db.models.query import QuerySet
from django_sphinx_db.backend.sphinx.compiler import SphinxWhereNode


class SphinxQuery(Query):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('where', SphinxWhereNode)
        super(SphinxQuery, self).__init__(*args, **kwargs)


class SphinxQuerySet(QuerySet):
    def __init__(self, model, **kwargs):
        kwargs.setdefault('query', SphinxQuery(model))
        super(SphinxQuerySet, self).__init__(model, **kwargs)

    def using(self, alias):
        # Ignore the alias. This will allow the Django router to decide
        # what db receives the query. Otherwise, when dealing with related
        # models, Django tries to force all queries to the same database.
        # This is the right thing to do in cases of master/slave or sharding
        # but with Sphinx, we want all related queries to flow to Sphinx,
        # never another configured database.
        return self._clone()


class SphinxManager(models.Manager):
    use_for_related_fields = True

    def get_queryset(self):
        # Determine which fields are sphinx fields (full-text data) and
        # defer loading them. Sphinx won't return them.
        # TODO: we probably need a way to keep these from being loaded
        # later if the attr is accessed.
        sphinx_fields = [field.name for field in self.model._meta.fields
                                if isinstance(field, SphinxField)]
        return SphinxQuerySet(self.model).defer(*sphinx_fields)


class SphinxField(models.TextField):
    pass


class SphinxModel(models.Model):
    class Meta:
        abstract = True

    objects = SphinxManager()
