# Create Google Cloud Platform project

## Use existing project
Subsequent use on a created project, in cloud shell:
```bash
$ gcloud config set project <your-project-id-here!>
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
$ gcloud services enable sqladmin.googleapis.com
$ gcloud services enable servicenetworking.googleapis.com
$ gcloud services enable cloudtasks.googleapis.com
$ gcloud services enable cloudsearch.googleapis.com
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

## Create peerings
Needed:
* Cloud SQL
* Service networking
```bash
$ gcloud compute networks peerings create \
  cloudsql-mysql-googleapis-com \
  --network=waste-vpc \
  --peer-project=speckle-umbrella-60
$ gcloud compute networks peerings create \
  servicenetworking-googleapis-com \
  --network=waste-vpc \
  --peer-project=l866559daaa2d5754p-tp
```


# Create service account credentials
Go to Project's _API & API settings_, _Credentials_, _Service Accounts_.

* Service account: _New service account_
* Service account name: `<your choice>`
* Roles:
  * _Cloud Run Invoker_
  * _Datastore User_
  * _Secret Manager Secret Accessor_
  * _App Engine Viewer_: for metadata requests
  * _Cloud Tasks Enqueuer_: for adding new jobs to task queue
  * _Service Account User_: for adding new jobs to task queue
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

Generate a random password of 50 characters, and store it without trailing newline:
```bash
$ apg -n 1 -a 1 -m 50 | \
  tr -d '\n' | \
  gcloud secrets create "django-secret_key" --data-file=-
```

# Cloud Storage

## Create bucket
To serve static resources over HTTP, create a bucket:
```bash
$ gsutil mb -l europe-north1 -c nearline -b on gs://waste-static
```

Make bucket accessibly by general public of the Internet:
```bash
$ gsutil iam ch allUsers:objectViewer gs://waste-static/
```

## Rsync `static/` to Cloud Bucket
**Note**: Make sure to affix the slash. This way rsync will copy **contents** of the directory.
```bash
$ gsutil rsync -r static/ gs://waste-static/
```

# Cloud Tasks
**Note**: Cloud Tasks is bound to App Engine app.

Confirm the location:
```bash
$ gcloud app describe
```
Will return: `locationId: europe-west3`

**Note 2**: 

## Create task queue
```bash
$ gcloud tasks queues create document
$ gcloud tasks queues create maintenance
$ gcloud tasks queues create urlfetch
```

# Cloud Search
Docs: https://github.com/google-cloudsearch/connector-api-python

## Create search schema
```bash
$ gcloud tasks queues create waste-d
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
$ django-admin startproject wasted_project .
$ ./manage.py startapp waste_d
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
* (optional) `GCP_RUN_HOSTS` to contain a comma-separated list of allowed hosts

```bash
$ python3 ./manage.py runserver
```

Example with environment defined on same line:
```bash
$ GOOGLE_CLOUD_PROJECT=waste-007 \
  GOOGLE_APPLICATION_CREDENTIALS=Waste-Google-service-account-credentials.json \
  python3 ./manage.py runserver
```

# Container build
Note: Installing Google Cloud SDK on local machine is recommended.
Instructions are at https://cloud.google.com/sdk/docs/install#rpm

## Trigger new build
```bash
$ gcloud builds submit --tag gcr.io/$GOOGLE_CLOUD_PROJECT/waste.d
```

## List images
List of all images:
```bash
$ gcloud container images list
```

List of tags of an image:
```bash
$ gcloud container images list-tags gcr.io/$GOOGLE_CLOUD_PROJECT/waste.d
```

## Promote a build result into latest:
```bash
$ gcloud container images add-tag --quiet \
  gcr.io/$GOOGLE_CLOUD_PROJECT/waste.d:<SHA-1 of image here> \
  gcr.io/$GOOGLE_CLOUD_PROJECT/waste.d:latest
```

# Cloud Run
**Note**: Cloud Tasks is bound to App Engine app.

## Deploy: Create Cloud Run service
Create a new Google Cloud Run service with given image:
```bash
gcloud run deploy waste-d \
  --platform managed --region europe-north1 \
  --image gcr.io/$GOOGLE_CLOUD_PROJECT/waste.d:latest \
  --port 8000 \
  --allow-unauthenticated \
  --vpc-connector=waste-to-vpc \
  --service-account <service-account@created-earlier> \
  --update-env-vars GOOGLE_CLOUD_PROJECT=$GOOGLE_CLOUD_PROJECT \
  --update-env-vars GCP_RUN_HOSTS=<waste-d-something-lz.a.run.app> \
  --update-env-vars GCP_TASKS_REGION=europe-west3 \
  --update-env-vars DJANGO_ENV=production
```

Docs: https://cloud.google.com/sdk/gcloud/reference/run/deploy

## Deploy: Update image
Update running image:
```bash
gcloud run deploy waste-d \
  --platform managed --region europe-north1 \
  --image gcr.io/$GOOGLE_CLOUD_PROJECT/waste.d:latest
```

## Connect to a GitHub repository
In GCP console:
1. Cloud Build
1. _Triggers_
1. _Connect Repository_
  1. Select your source: _GitHub (Cloud Build GitHub App)_
1. In GitHub, Install Google Cloud Build application
   * Disclaimer:
     I understand that GitHub content for the selected repositories will be transferred to this GCP project to provide the connected service.
     Members of this GCP project with sufficient permissions will be able to create and run triggers on these repositories, based on transferred GitHub content.
     I also understand that content from all GitHub app triggers in this GCP project may be transferred to GitHub in order to provide functionality like showing trigger names in GitHub build results.
     This will apply to all existing and future GitHub App triggers in this project.
1. Create Push Trigger
1. Done!

Now a new Docker-image is built on every push.

## Local testing of an image

1. Install Google Cloud SDK
1. `CLOUDSDK_PYTHON=python2 gcloud auth login`
1. `CLOUDSDK_PYTHON=python2 gcloud auth configure-docker`

Now you can pull:

`CLOUDSDK_PYTHON=python2 docker pull gcr.io/$GOOGLE_CLOUD_PROJECT/waste.d`

# Custom domain setup with complimentary TLS-certificate

## Verify the domain
Docs: https://cloud.google.com/identity/docs/verify-domain

List verified domains:
```bash
$ gcloud domains list-user-verified
```

## Map domain to a Google Cloud Run service
```bash
$ gcloud beta run domain-mappings create \
  --platform managed --region europe-north1 \
  --service waste-d \
  --domain <your own domain>
```

Output:
```bash
Waiting for certificate provisioning. You must configure your DNS records for certificate issuance to begin.
NAME     RECORD TYPE  CONTENTS
waste-d  A            x4.y4.z4.å4
waste-d  A            x4.y4.z4.å4
waste-d  A            x4.y4.z4.å4
waste-d  A            x4.y4.z4.å4
waste-d  AAAA         2001:x6:y6:z6::15
waste-d  AAAA         2001:x6:y6:z6::15
waste-d  AAAA         2001:x6:y6:z6::15
waste-d  AAAA         2001:x6:y6:z6::15
```

## Add records to DNS
That's something you need to figure out yourself!

## Wait
An automated system in Google will verify DNS-records.
When set ok, mapping will go green and a TLS-certificate will be issued to the domain.
