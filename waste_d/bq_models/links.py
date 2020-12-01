from google.cloud.bigquery import SchemaField
from .abstract.model import BQModel


class Links(BQModel):
    _table_name = 'links'
    _schema = [
        # SchemaField('_PARTITIONTIME', 'TIMESTAMP', mode='required'),
        SchemaField('platform', 'STRING', mode='required'),
        SchemaField('chat', 'STRING'),
        SchemaField('channel', 'STRING', mode='required'),
        SchemaField('user', 'STRING', mode='required'),
        SchemaField('url', 'STRING', mode='required'),
        SchemaField('date', 'DATETIME'),
        SchemaField('title', 'STRING'),
        SchemaField('comment', 'STRING'),
        SchemaField('tags', 'RECORD', mode='nullable',
                    fields=(
                        SchemaField('tag', 'STRING'),
                    )),
        SchemaField('rate', 'INT64'),
    ]

    def __init__(self, client=None, dataset_id=None):
        print("Links __init__ going for super()!")
        super(Links, self).__init__(client=client, dataset_id=dataset_id)
        self.table = self.dataset.table(Links._table_name)

        print("Links __init__!")
        from pprint import pprint
        pprint(self._data)

    def insert(self):
        errors = self.client.insert_rows(self._table_name, rows_to_insert)
        if not errors == []:
            print(errors)
            raise ValueError('Failed to insert data into BigQuery!')
