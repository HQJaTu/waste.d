from django.conf import settings
from google.cloud import bigquery


class BQModel:

    _table_name = None
    _schema = None

    client = None
    dataset = None

    def __init__(self, client=None, dataset_id=None):
        if client:
            self.client = client
        self.dataset = self.get_dataset(dataset_id=dataset_id)
        self.table = None
        self._data = {}
        self._init_fields()

    def _init_fields(self):
        if not hasattr(self, '_schema') or not self._schema:
            raise ValueError("No schema!")

        print("Doing schema!")
        for field in self._schema:
            field_name = field.name
            self._data[field_name] = None

    def __setattr__(self, key, value):
        if isinstance(self, BQModel):
            return object.__setattr__(self, key, value)

        reserved = ['client', 'dataset', 'table', '_data']
        if key not in reserved and key in self._data:
            self.set_attr(key, value)
        else:
            object.__setattr__(self, key, value)

    def __getattribute__(self, key):
        if isinstance(self, BQModel):
            return object.__getattribute__(self, key)

        reserved = ['client', 'dataset', 'table', '_data', ]
        if key not in reserved and key in self._data:
            return self.__dict__['get_attr'](self, key)
        return object.__getattribute__(self, key)

    def get_attr(self, key):
        r = self._data[key]
        # logic
        return r

    def set_attr(self, key, value):
        # logic
        self._data[key] = value

    def get_dataset(self, dataset_id=None):
        if BQModel.dataset:
            return BQModel.dataset

        if not BQModel.client:
            if self.client:
                BQModel.client = self.client
            else:
                BQModel.client = bigquery.Client()

        if dataset_id:
            dataset_id_to_use = dataset_id
        else:
            dataset_id_to_use =settings.BG_DATASET_ID
        BQModel.dataset = BQModel.client.get_dataset(dataset_id_to_use)

        return BQModel.dataset
