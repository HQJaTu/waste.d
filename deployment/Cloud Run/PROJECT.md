# Create Google Cloud Platform project

## Create the project

Creation in cloud shell:
```bash
$ gcloud config set project <your-project-id-here!>
```

## Use existing project
Subsequent use on a created project, in cloud shell:
```bash
$ gcloud config set project <your-project-id-here!>
$ cd waste.d/
$ source venv/bin/activate
```

# Enable required Cloud APIs
In cloud shell:
```bash
$ gcloud services enable run.googleapis.com
$ gcloud services enable logging.googleapis.com
$ gcloud services enable vpcaccess.googleapis.com
$ gcloud services enable dns.googleapis.com
$ gcloud services enable datastore.googleapis.com
$ gcloud services enable cloudbuild.googleapis.com
$ gcloud services enable secretmanager.googleapis.com
```

# VPC

## Create VPC
```bash
$ gcloud compute networks create \
  waste-vpc \
  --bgp-routing-mode=regional \
  --subnet-mode=custom
```

## Create subnet
```bash
$ gcloud compute networks subnets create \
  waste-subnet \
  --region=europe-north1 \
  --network waste-vpc \
  --range=10.10.0.0/20 \
  --enable-private-ip-google-access \
  --private-ipv6-google-access-type enable-outbound-vm-access
```

## Create connector
```bash
$ gcloud compute networks vpc-access connectors create \
  waste-to-vpc \
  --network waste-vpc \
  --region europe-north1 \
  --range 10.10.248.0/28
```

# Create service account credentials
Go to Project's _API & API settings_, _Credentials_, _Service Accounts_.

* Service account: _New service account_
* Service account name: `<your choice>`
* Roles:
  * _Cloud Run Invoker_
  * _Datastore User_
  * _Secret Manager Secret Accessor_
* Service account ID: `<default is ok>`
* Key Type: _JSON_

Save resulting JSON-file into `Waste-Google-service-account-credentials.json`.

**Note:** The key file is available once. Your window-of-opportunity is immediately after creation.
If you choose to misplace the resulting file, it's gone forever!

**Note 2:** You can create any number of keys for a service account to recover any possibly lost ones.

# Datastore

## Select Cloud Firestore operating mode
No API-call available!

In web-GUI, select: _Datastore mode_

## (future) CLI select Cloud Firestore operating mode
Alpha-API has command:
```bash
$ gcloud alpha datastore databases create
```

It will not work similarily as GUI:
```bash
ERROR: gcloud crashed (AppEngineAppDoesNotExist): You must first create a Google App Engine app by running:
gcloud app create
```

## Indexes
Create datastore indexes:
```bash
$ gcloud datastore indexes create deployment/Datastore/index.yaml
```

List created indexes:
```bash
$ gcloud datastore indexes list
```

Wait for `state: CREATING` to change into `state: READY`.

Describe single index:
```bash
$ gcloud datastore indexes describe <-one-of-your-indexes->
```

# Secrets Manager

## Create Django SECRET_KEY
Install apg:
```bash
$ sudo apt-get install apg
```

Generate a random password of 50 characters, and store it:
```bash
$ apg -n 1 -a 1 -m 50 | gcloud secrets create "django-secret_key" --data-file=-
```

# Python:

## Create
In cloud shell:
```bash
$ mkdir ~/waste.d
$ cd waste.d/
$ virtualenv venv
$ source venv/bin/activate
$ pip freeze > requirements.txt
$ django-admin startproject waste_d .
```

Quit virtual environment:
```bash
$ deactivate
```

## Use existing
```bash
$ source venv/bin/activate
```

## Run server
Define environment variables:
* `GOOGLE_CLOUD_PROJECT` to contain the GCP Project ID
* `GOOGLE_APPLICATION_CREDENTIALS` to point to the JSON-file containing app credentials.

```bash
$ python3 ./manage.py runserver
```

Example with environment defined on same line:
```bash
$ GOOGLE_CLOUD_PROJECT=waste-007 \
  GOOGLE_APPLICATION_CREDENTIALS=Waste-Google-service-account-credentials.json \
  python3 ./manage.py runserver
```

# Container

## Trigger new build
```bash
$ gcloud builds submit --tag gcr.io/$GOOGLE_CLOUD_PROJECT/waste.d
```

## List images
```bash
$ gcloud container images list
```

## Deploy
Create new Google Cloud Run service
```bash
gcloud run deploy django-cloudrun --platform managed --region europe-north1 \
  --image gcr.io/$GOOGLE_CLOUD_PROJECT/django-test \
  --allow-unauthenticated
```
