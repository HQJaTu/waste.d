#!/usr/bin/env python3

import sys
import argparse
import logging
from google.cloud import bigquery  # pip3 install google-cloud-bigquery
from google.cloud.bigquery import TimePartitioningType, SchemaField

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

    # Data types: https://cloud.google.com/bigquery/docs/schemas
    # Mode: https://cloud.google.com/bigquery/docs/reference/rest/v2/tables#TableFieldSchema.FIELDS.mode
    # Possible values include NULLABLE, REQUIRED and REPEATED.
    table_schema = Links._schema
    from pprint import pprint
    pprint(table_schema)

    links = Links(client=client, dataset_id=dataset_id)
    pprint(links.platform)
    exit(1)

    table_ref = dataset.table('links')
    table = bigquery.Table(table_ref, schema=table_schema)
    table.time_partitioning = bigquery.table.TimePartitioning(type_=TimePartitioningType.DAY)
    log.info("Create table")
    table = client.create_table(table, exists_ok=True)

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
