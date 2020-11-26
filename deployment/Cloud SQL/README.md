# GCP Cloud SQL

## (prerequisite) Enable API
(If you haven't done so already.)
```bash
$ gcloud services enable sqladmin.googleapis.com
```

## (prerequisite) Create root password
Install apg:
```bash
$ sudo apt-get install apg
```

Generate a random password of 32 characters (MySQL max.), and store it without trailing newline:
```bash
$ apg -n 1 -a 1 -M ncl -m 32 | \
  tr -d '\n' | \
  gcloud secrets create "mysql-root" --data-file=-
```

## Create Cloud SQL instance
My own ISP's network:
```bash
$ elisa_fiber_net=62.248.128.0/17
```

Create:
```bash
$ gcloud beta sql instances create \
    waste-d \
    --region=europe-north1 \
    --tier=db-f1-micro \
    --database-version=MYSQL_8_0 \
    --availability-type=zonal \
    --assign-ip \
    --network=projects/$GOOGLE_CLOUD_PROJECT/global/networks/waste-vpc \
    --authorized-networks="$elisa_fiber_net" \
    --storage-type=HDD \
    --backup \
    --backup-start-time=02:06 \
    --storage-size=10 \
    --root-password="$(gcloud secrets versions access latest --secret='mysql-root')"
```

Note: Instance will exist for a week after deletion.

Error:
Invalid request: Incorrect Service Networking config for instance: NETWORK_NOT_PEERED.

## Take a record of the private IPv4 address assigned
The IP-address will be needed for VPC-connection from Cloud Run.

## Create a database
```bash
$ gcloud sql databases create waste.d --instance=waste-d --collation=utf8_general_ci
```

## Add Django-user
Create password (no trailing newline):
```bash
$ apg -n 1 -a 1 -M ncl -m 32 | \
  tr -d '\n' | \
  gcloud secrets create "mysql-app-user" --data-file=-
```

Add user _wappd_:
```bash
$ gcloud sql users create wappd \
  --instance=waste-d \
  --password="$(gcloud secrets versions access latest --secret='mysql-app-user')"
```

## Connect to created instance
```bash
$ gcloud sql connect wasted-d --user=root --quiet
```

## Have Django ORM create schema
In Django-lingo, the operation is "migrate":
```bash
$ GOOGLE_CLOUD_PROJECT=waste-007 \
  GOOGLE_APPLICATION_CREDENTIALS=Waste-Google-service-account-credentials.json \
  python3 manage.py migrate
```

Success will look like this:
```text
Operations to perform:
  Apply all migrations: admin, auth, contenttypes, sessions
Running migrations:
  Applying contenttypes.0001_initial... OK
  Applying auth.0001_initial... OK
  Applying admin.0001_initial... OK
  Applying admin.0002_logentry_remove_auto_add... OK
  Applying admin.0003_logentry_add_action_flag_choices... OK
  Applying contenttypes.0002_remove_content_type_name... OK
  Applying auth.0002_alter_permission_name_max_length... OK
  Applying auth.0003_alter_user_email_max_length... OK
  Applying auth.0004_alter_user_username_opts... OK
  Applying auth.0005_alter_user_last_login_null... OK
  Applying auth.0006_require_contenttypes_0002... OK
  Applying auth.0007_alter_validators_add_error_messages... OK
  Applying auth.0008_alter_user_username_max_length... OK
  Applying auth.0009_alter_user_last_name_max_length... OK
  Applying auth.0010_alter_group_name_max_length... OK
  Applying auth.0011_update_proxy_permissions... OK
  Applying auth.0012_alter_user_first_name_max_length... OK
  Applying sessions.0001_initial... OK
```

# Django users

## Super(l)user
```bash
$ GOOGLE_CLOUD_PROJECT=waste-007 \
  GOOGLE_APPLICATION_CREDENTIALS=Waste-Google-service-account-credentials.json \
  python3 manage.py createsuperuser --username admin --email django-admin@example.com
```

## API-user
Enter Django-shell:
```bash
$ GOOGLE_CLOUD_PROJECT=waste-007 \
  GOOGLE_APPLICATION_CREDENTIALS=Waste-Google-service-account-credentials.json \
  python3 manage.py shell
```

In the shell, run raw python:
```python
from django.contrib.auth.models import User
user=User.objects.create_user('eggdrop', password='-choose-wisely-!')
user.is_superuser=False
user.is_staff=False
user.save()
```

Auth token:
```bash
$ GOOGLE_CLOUD_PROJECT=waste-007 \
  GOOGLE_APPLICATION_CREDENTIALS=Waste-Google-service-account-credentials.json \
  python3 manage.py drf_create_token eggdrop
```

# Django SQL-tables

## Create code for ORM migrations
```bash
$ GOOGLE_CLOUD_PROJECT=waste-007 \
  GOOGLE_APPLICATION_CREDENTIALS=Waste-Google-service-account-credentials.json \
  python3 manage.py makemigrations
```

## Migrate SQL
```bash
$ GOOGLE_CLOUD_PROJECT=waste-007 \
  GOOGLE_APPLICATION_CREDENTIALS=Waste-Google-service-account-credentials.json \
  python3 manage.py makemigrations
```
