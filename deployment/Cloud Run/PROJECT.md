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

# Enable Cloud APIs
In cloud shell:
```bash
$ gcloud services enable run.googleapis.com
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
```bash
$ python3 ./manage.py runserver
```
