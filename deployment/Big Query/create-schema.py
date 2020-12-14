#!/usr/bin/env python3

import os
import sys
import argparse
import logging
from google.cloud import bigquery  # pip3 install google-cloud-bigquery
from google.cloud.bigquery import TimePartitioningType, SchemaField
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wasted_project.settings')
django.setup()

from waste_d.bq_models import Links

log = logging.getLogger(__name__)


def _setup_logger():
    log_formatter = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(log_formatter)
    console_handler.propagate = False
    logging.getLogger().addHandler(console_handler)

    log.setLevel('DEBUG')


def init_bigquery(dataset_id, credentials_file=None):
    if credentials_file:
        client = bigquery.Client.from_service_account_json(credentials_file)
    else:
        client = bigquery.Client()
    project = client.project

    # Get a handle into dataset.
    dataset = client.get_dataset(dataset_id)
    log.debug("Got dataset")

    links = Links(client=client, dataset=dataset)
    do_insert = False
    do_search_by = None # '123456-1234568'
    if do_insert:
        links.doc_id = '123456-1234568'
        links.platform = 'irc'
        links.channel = '#armila'
        links.user = 'JaTu'
        links.url = 'https://docs.microsoft.com/en-us/windows-hardware/drivers/display/overriding-monitor-edids'
        from datetime import datetime
        links.date = datetime.now()
        links.title = 'Overriding Monitor EDIDs with an INF - Windows drivers | Microsoft Docs'
        links.comment = 'jees-bah!'
        # Good for:
        # tags = BQRecordField(
        #         mode='REPEATED',
        #         fields=(
        #             BQStringField(name='tag'),
        #             BQStringField(name='type'),
        #         )
        #     )
        #
        #links.tags = [{'tag': 'a-tagi'}, {'tag': 'b-tagi'}]
        # Good for:
        # tags = BQRecordField(
        #         mode='REPEATED',
        #         fields=(
        #             BQStringField(name='tag'),
        #         )
        #     )
        #
        links.tags = [['g-tagi'], ['h-tagi']]
        table_schema = links.get_schema()

        from pprint import pprint
        pprint(links.get_values())

    log.info("Create table")
    table = links.create_table(exists_ok=True, time_partitioning=TimePartitioningType.DAY)

    if do_insert:
        # Test-insert the above data
        links.insert()

    if do_search_by:
        links.get_by_doc_id(do_search_by)

    return client, table


def main():
    parser = argparse.ArgumentParser(description='OpenDNSSEC BIND slave zone configurator')
    parser.add_argument('--bigquery-json-credentials', metavar='GOOGLE-JSON-CREDENTIALS-FILE',
                        help='Mandatory. JSON-file with Google BigQuery API Service Account credentials.')
    parser.add_argument('--bigquery-dataset-id', metavar='GOOGLE-BIGQUERY-DATASET-ID',
                        required=True,
                        help='Mandatory. BigQuery dataset ID to store data into.')
    parser.add_argument('--verbose', action='store_true', default=False,
                        help='Output more debug-style information.')
    args = parser.parse_args()

    _setup_logger()
    log.info("Begin")

    # Init Google BigQuery
    bq_client, bq_table = init_bigquery(args.bigquery_dataset_id, args.bigquery_json_credentials)

    log.info("Done")


if __name__ == '__main__':
    main()
