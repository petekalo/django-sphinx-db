from django.db.models.sql import compiler
from django.db.models.sql.where import WhereNode
from django.db.models.sql.where import EmptyResultSet
#from django.db.models.sql.expressions import SQLEvaluator


class SphinxWhereNode(WhereNode):
    def sql_for_columns(self, data, qn, connection):
        table_alias, name, db_type = data
        return connection.ops.field_cast_sql(db_type) % name

    def as_sql(self, qn, connection):
        # TODO: remove this when no longer needed.
        # This is to remove the parenthesis from where clauses.
        # http://sphinxsearch.com/bugs/view.php?id=1150
        sql, params = super(SphinxWhereNode, self).as_sql(qn, connection)
        if sql and sql[0] == '(' and sql[-1] == ')':
            # Trim leading and trailing parenthesis:
            sql = sql[1:]
            sql = sql[:-1]
        return sql, params

    def make_atom(self, child, qn, connection):
        """
        Transform search, the keyword should not be quoted.
        """
        lvalue, lookup_type, value_annot, params_or_value = child
        sql, params = super(SphinxWhereNode, self).make_atom(child, qn, connection)
        if lookup_type == 'search':
            if hasattr(lvalue, 'process'):
                try:
                    lvalue, params = lvalue.process(lookup_type, params_or_value, connection)
                except:
                    raise
# note EmptyShortCircuit was removed in 1.9, will leave a raise:
#                except EmptyShortCircuit:
#                    raise EmptyResultSet
            if isinstance(lvalue, tuple):
                # A direct database column lookup.
                field_sql = self.sql_for_columns(lvalue, qn, connection)
            else:
                # A smart object with an as_sql() method.
                field_sql = lvalue.as_sql(qn, connection)
            # TODO: There are a couple problems here.
            # 1. The user _might_ want to search only a specific field.
            # 2. However, since Django requires a field name to use the __search operator
            #    There is no way to do a search in _all_ fields.
            # 3. Because, using multiple __search operators is not supported.
            # So, we need to merge multiped __search operators into a single MATCH(), we
            # can't do that here, we have to do that one level up...
            # Ignore the field name, search all fields:
            params = ('@* %s' % params[0], )
            # _OR_ respect the field name, and search on it:
            #params = ('@%s %s' % (field_sql, params[0]), )
        return sql, params


class SphinxQLCompiler(compiler.SQLCompiler):
    def get_columns(self, *args, **kwargs):
        columns = super(SphinxQLCompiler, self).get_columns(*args, **kwargs)
        for i, column in enumerate(columns):
            if '.' in column:
                columns[i] = column.partition('.')[2]
        return columns

    def quote_name_unless_alias(self, name):
        # TODO: remove this when no longer needed.
        # This is to remove the `` backticks from identifiers.
        # http://sphinxsearch.com/bugs/view.php?id=1150
        return name

# Set SQLCompiler appropriately, so queries will use the correct compiler.
SQLCompiler = SphinxQLCompiler


class SQLInsertCompiler(compiler.SQLInsertCompiler, SphinxQLCompiler):
    pass


class SQLDeleteCompiler(compiler.SQLDeleteCompiler, SphinxQLCompiler):
    pass


class SQLUpdateCompiler(compiler.SQLUpdateCompiler, SphinxQLCompiler):
    def as_sql(self):
        qn = self.connection.ops.quote_name
        opts = self.query.model._meta
        result = ['REPLACE INTO %s' % qn(opts.db_table)]
        # This is a bit ugly, we have to scrape information from the where clause
        # and put it into the field/values list. Sphinx will not accept an UPDATE
        # statement that includes full text data, only INSERT/REPLACE INTO.
        lvalue, lookup_type, value_annot, params_or_value = self.query.where.children[0].children[0]
        (table_name, column_name, column_type), val = lvalue.process(lookup_type, params_or_value, self.connection)
        fields, values, params = [column_name], ['%s'], [val[0]]
        # Now build the rest of the fields into our query.
        for field, model, val in self.query.values:
            if hasattr(val, 'prepare_database_save'):
                val = val.prepare_database_save(field)
            else:
                val = field.get_db_prep_save(val, connection=self.connection)

            # Getting the placeholder for the field.
            if hasattr(field, 'get_placeholder'):
                placeholder = field.get_placeholder(val, self.connection)
            else:
                placeholder = '%s'

            # deprecated #14030
            #if hasattr(val, 'evaluate'):
            #    val = SQLEvaluator(val, self.query, allow_joins=False)
            name = field.column
            if hasattr(val, 'as_sql'):
                sql, params = val.as_sql(qn, self.connection)
                values.append(sql)
                params.extend(params)
            elif val is not None:
                values.append(placeholder)
                params.append(val)
            else:
                values.append('NULL')
            fields.append(name)
        result.append('(%s)' % ', '.join(fields))
        result.append('VALUES (%s)' % ', '.join(values))
        return ' '.join(result), params


class SQLAggregateCompiler(compiler.SQLAggregateCompiler, SphinxQLCompiler):
    pass

# not in Django 1.8.6:
#class SQLDateCompiler(compiler.SQLDateCompiler, SphinxQLCompiler):
    #pass
