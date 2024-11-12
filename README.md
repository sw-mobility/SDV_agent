# SDV_agent
Repository for SDV agent


Prerequisite
---
- S3 BUCKET NAME
- AWS ACCESS KEY ID
- AWS SECRET ACCESS KEY

How to Start Data Upload
---
1. Save the image files to /SDV_agent/data/images folder for analysis
2. Excute the below
```sh
sh start.sh
```

Data Download API
---
You can download the uploaded image files by syncronizing a directory of local file system with the directory of S3.
The Sync API is implemented in `SDV_agent/tango/run_sync.py`.
Please refer to the examples below.

```python
from run_sync import S3DirSync

sync = S3DirSync(bucket={BUCKET_NAME}, access_key={AWS_ACCESS_KEY_ID}, secret_key={AWS_SECRET_ACCESS_KEY})
sync.start(s3_dir={S3_DIR_NAME}, local_dir={LOCAL_DIR_NAME}, check_period={SYNC_PERIOD_TIME})
```

You can assign a callback function if the number of the updated files exceeds a threshold.
```python
sync.start(s3_dir={S3_DIR_NAME}, local_dir={LOCAL_DIR_NAME}, check_period={SYNC_PERIOD_TIME}, \
           callback_func={CALLBACK_FUNC}, callback_threshold={CALLBACK_THRESHOLD})
```

The Sync API ignores the update by the sync initiation. 
So, the callback function would not be called by the initiation. 
If you want to call the function by it, use the `ignore_update_by_init` option as shown below:
```python
sync.start(s3_dir={S3_DIR_NAME}, local_dir={LOCAL_DIR_NAME}, check_period={SYNC_PERIOD_TIME}, ignore_update_by_init=False)
```



