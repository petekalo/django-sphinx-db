from django.db.backends.mysql.introspection import *
from django.db.backends.mysql.introspection import DatabaseIntrospection as MYSQLDatabaseIntrospection
from django.utils.functional import cached_property


class DatabaseIntrospection(MYSQLDatabaseIntrospection):

    def get_table_list(self, cursor):
        """
        Returns a list of table and view names in the current database.
        """
        cursor.execute("SHOW TABLES")
        return [TableInfo(row[0], {'BASE TABLE': 't', 'VIEW': 'v'}.get(row[1]))
                for row in cursor.fetchall()]


