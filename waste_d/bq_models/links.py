from google.cloud import bigquery
from .abstract.model import BQModel
from .abstract.fields import *


class Links(BQModel):
    _PARTITIONTIME = BQPartitionTimestampField()
    doc_id = BQStringField(mode='required')
    platform = BQStringField(mode='required')
    chat = BQStringField()
    channel = BQStringField(mode='required')
    user = BQStringField(mode='required')
    url = BQStringField(mode='required')
    date = BQDatetimeField()
    title = BQStringField()
    comment = BQStringField()
    tags = BQRecordField(
        mode='REPEATED',
        fields=(
            BQStringField(name='tag'),
        )
    )
    rate = BQIntegerField()

    def find_by_doc_id(self, doc_id):
        query = """select *
from `waste_d_links`
where doc_id = @docid"""
        result = self.query(query, params={'docid': doc_id})
        if result.total_rows != 0:
            return False
        BQModel.row_to_model(self, result[0])

        return True

    def get_by_url(self, platform, chat, channel, url):
        if not chat:
            chat = ''
        query = """select *
from `waste_d_links`
where platform = @platform
and chat = @chat
and channel = @channel
and url = @url"""
        qp = {
            'platform': platform,
            'chat': chat,
            'channel': channel,
            'url': url,
        }

        result = self.query(query, params=qp)

        rows = []
        for row in result:
            link = Links()
            BQModel.row_to_model(link, row)
            rows.append(link)

        return rows
