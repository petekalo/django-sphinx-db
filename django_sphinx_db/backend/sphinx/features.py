from django.db.backends.mysql.features import DatabaseFeatures as MYSQLDatabaseFeatures
from django.utils.functional import cached_property

class DatabaseFeatures(MYSQLDatabaseFeatures):

    @cached_property
    def is_sql_auto_is_null_enabled(self):
        return 0
