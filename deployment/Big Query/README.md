# Big Query

## Create Dataset

```bash
bq mk \
  --location=europe-north1 \
  --dataset \
  --description "Waste.d urls" \
  $GOOGLE_CLOUD_PROJECT:wasted_prod
```

