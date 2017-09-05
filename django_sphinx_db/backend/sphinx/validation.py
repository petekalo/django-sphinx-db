from django.db.backends.mysql.validation import *
from django.db.backends.mysql.validation import DatabaseValidation as MYSQLDatabaseIntrospection

class DatabaseValidation(MYSQLDatabaseIntrospection):
    def _check_sql_mode(self, **kwargs):
        '''sphinx does not appear to support this sql_mode validation, skipped'''
        return []
