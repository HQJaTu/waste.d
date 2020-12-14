from django.conf import settings
from django.db.models.base import ModelBase, ModelState, DEFERRED
from django.db.models.signals import pre_init, post_init
from django.core.exceptions import FieldDoesNotExist
from google.cloud import bigquery
from .fields import *


class BQModel(metaclass=ModelBase):
    bq_client = None
    bq_dataset = None
    bq_table = None
    bq_time_partitioning = None

    def __init__(self, *args, dataset=None, client=None, **kwargs):
        # Alias some things as locals to avoid repeat global lookups
        cls = self.__class__
        opts = self._meta
        _setattr = setattr
        _DEFERRED = DEFERRED

        if dataset:
            self.bq_dataset = dataset
        if client:
            self.bq_client = client

        pre_init.send(sender=cls, args=args, kwargs=kwargs)

        # Set up the storage for instance state
        self._state = ModelState()

        # There is a rather weird disparity here; if kwargs, it's set, then args
        # overrides it. It should be one or the other; don't duplicate the work
        # The reason for the kwargs check is that standard iterator passes in by
        # args, and instantiation for iteration is 33% faster.
        if len(args) > len(opts.concrete_fields):
            # Daft, but matches old exception sans the err msg.
            raise IndexError("Number of args exceeds number of fields")

        if not kwargs:
            fields_iter = iter(opts.concrete_fields)
            # The ordering of the zip calls matter - zip throws StopIteration
            # when an iter throws it. So if the first iter throws it, the second
            # is *not* consumed. We rely on this, so don't change the order
            # without changing the logic.
            for val, field in zip(args, fields_iter):
                if val is _DEFERRED:
                    continue
                _setattr(self, field.attname, val)
        else:
            # Slower, kwargs-ready version.
            fields_iter = iter(opts.fields)
            for val, field in zip(args, fields_iter):
                if val is _DEFERRED:
                    continue
                _setattr(self, field.attname, val)
                kwargs.pop(field.name, None)

        # Now we're left with the unprocessed fields that *must* come from
        # keywords, or default.

        for field in fields_iter:
            is_related_object = False
            # Virtual field
            if field.attname not in kwargs and field.column is None:
                continue
            if kwargs:
                try:
                    val = kwargs.pop(field.attname)
                except KeyError:
                    # This is done with an exception rather than the
                    # default argument on pop because we don't want
                    # get_default() to be evaluated, and then not used.
                    # Refs #12057.
                    val = field.get_default()
            else:
                val = field.get_default()

            if val is not _DEFERRED:
                _setattr(self, field.attname, val)

        if kwargs:
            property_names = opts._property_names
            for prop in tuple(kwargs):
                try:
                    # Any remaining kwargs must correspond to properties or
                    # virtual fields.
                    if prop in property_names or opts.get_field(prop):
                        if kwargs[prop] is not _DEFERRED:
                            _setattr(self, prop, kwargs[prop])
                        del kwargs[prop]
                except (AttributeError, FieldDoesNotExist):
                    pass
            for kwarg in kwargs:
                raise TypeError("%s() got an unexpected keyword argument '%s'" % (cls.__name__, kwarg))
        super().__init__()
        post_init.send(sender=cls, instance=self)

    @classmethod
    def check(cls, **kwargs):
        errors = []
        return errors

    def get_dataset(self, dataset_id=None):
        if self.bq_dataset:
            return self.bq_dataset
        if BQModel.bq_dataset:
            self.bq_dataset = BQModel.bq_dataset

            return BQModel.bq_dataset

        if not BQModel.bq_client:
            if self.bq_client:
                BQModel.bq_client = self.bq_client
            else:
                BQModel.bq_client = bigquery.Client()

        if dataset_id:
            dataset_id_to_use = dataset_id
        else:
            dataset_id_to_use = settings.BG_DATASET_ID
        BQModel.bq_dataset = BQModel.bq_client.get_dataset(dataset_id_to_use)
        self.bq_dataset = BQModel.bq_dataset

        return BQModel.bq_dataset

    def get_schema(self):
        opts = self._meta

        schema = []
        for prop in opts.get_fields():
            if isinstance(prop, BQPartitionTimestampField):
                continue
            name = prop.name
            type = prop.bq_type
            mode = prop.mode
            desc = prop.descr
            fields = ()
            if isinstance(prop, BQRecordField):
                fields_list = []
                if not isinstance(prop.fields, tuple):
                    raise ValueError("Record %s fields isn't a tuple!" % name)

                for record in list(prop.fields):
                    record_name = record.name
                    record_type = record.bq_type
                    record_mode = record.mode
                    record_desc = record.descr
                    record_field = bigquery.SchemaField(record_name, record_type,
                                                        mode=record_mode, description=record_desc,
                                                        fields=())
                    fields_list.append(record_field)
                fields = tuple(fields_list)
            field = bigquery.SchemaField(name, type, mode=mode, description=desc, fields=fields)
            schema.append(field)

        return schema

    def get_values(self):
        opts = self._meta

        values = []
        for prop in opts.get_fields():
            if isinstance(prop, BQPartitionTimestampField):
                continue

            if isinstance(prop, BQDatetimeField):
                val = getattr(self, prop.name)
            elif isinstance(prop, BQIntegerField):
                val = getattr(self, prop.name)
                if not val:
                    val = None
                else:
                    val = int(val)
            elif isinstance(prop, BQRecordField):
                val = getattr(self, prop.name)
            else:
                val = getattr(self, prop.name)
            values.append(val)

        return values

    def get_table(self, dataset=None):
        if self.bq_table:
            return self.bq_table

        # Go get it from dataset
        if not self.bq_dataset and not dataset:
            raise ValueError("No dataset!")
        if not self.bq_dataset:
            self.bq_dataset = dataset
        self.bq_table = bigquery.Table(self.bq_dataset.table(self.get_table_name()), schema=self.get_schema())

        return self.bq_table

    def get_table_name(self):
        opts = self._meta

        return opts.db_table

    def create_table(self, dataset=None, client=None, exists_ok=False, time_partitioning=None):
        if not self.bq_dataset and not dataset:
            raise ValueError("No dataset!")
        if not self.bq_client and not client:
            raise ValueError("No client!")

        table_in = self.get_table()
        if time_partitioning:
            self.bq_time_partitioning = time_partitioning
        if self.bq_time_partitioning:
            table_in.time_partitioning = bigquery.table.TimePartitioning(type_=bigquery.TimePartitioningType.DAY)
        table_out = self.bq_client.create_table(table_in, exists_ok=exists_ok)

        return table_out

    def insert(self, dataset=None, client=None):
        if not self.bq_dataset and not dataset:
            raise ValueError("No dataset!")
        if not self.bq_client and not client:
            raise ValueError("No client!")

        values = self.get_values()

        errors = self.bq_client.insert_rows(self.get_table(), [values])
        if not errors == []:
            raise ValueError('Failed to insert data into BigQuery! Errors: %s' % ', '.join(errors))

    def query(self, query, params={}):
        job_config = bigquery.QueryJobConfig()
        job_config.default_dataset = self.get_dataset()
        # Write results to a table:
        # job_config.destination = self.get_table(ds)
        # job_config.create_disposition = 'CREATE_IF_NEEDED'
        # job_config.write_disposition = 'WRITE_APPEND'

        if params:
            query_parameters = []
            for param, param_value in params.items():
                param_out = bigquery.ScalarQueryParameter(param, "STRING", param_value)
                query_parameters.append(param_out)

            job_config.query_parameters = query_parameters

        job = self.bq_client.query(query, job_config=job_config)
        result = job.result()

        return result

    @staticmethod
    def row_to_model(model, row):
        if not isinstance(row, bigquery.Row):
            raise ValueError("Need a Row-object!")
        opts = model._meta
        for prop in opts.get_fields():
            if isinstance(prop, BQPartitionTimestampField):
                continue
            name = prop.name
            setattr(model, name, row[name])
