import boto3
import os
import threading

from time import sleep
from datetime import datetime


class S3DirSync:
    def __init__(self, bucket:[str], access_key:[str], secret_key:[str]):
        self.bucket = bucket
        self.access_key = access_key
        self.secret_key = secret_key
        self.num_update = 0
        self.callback_in_progress = []

        # aws session open
        aws_session = boto3.Session(aws_access_key_id=self.access_key,
                                    aws_secret_access_key=self.secret_key)
        self.client = aws_session.client('s3')

    def start(self, s3_dir:[str], local_dir:[str], check_period:[int]=300,
              callback_func=None, callback_threshold:[int]=None, ignore_update_by_init=True):
        # directory parameter formatting
        self.s3_dir, self.local_dir = self._dir_format(s3_dir, local_dir)

        # initiate file_list and directory structure of local_dir
        self.file_list = set()
        if os.path.isdir(self.local_dir):
            for obj in os.scandir(self.local_dir):
                if obj.is_file():
                    self.file_list.add(obj)
        else:
            os.makedirs(self.local_dir)

        while True:
            # check whether s3_dir is udpated
            update_list = []
            for content in self.client.list_objects_v2(Bucket=self.bucket, Prefix=self.s3_dir)['Contents']:
                obj_name = content['Key'].split('/')[-1]
                if obj_name in self.file_list:
                    pass
                else:
                    update_list.append(content['Key'])
                    self.file_list.add(obj_name)

            # download updated data
            if len(update_list) > 0:
                update_trd = threading.Thread(target=self._update,
                                              args=(update_list, callback_func, callback_threshold, ignore_update_by_init),
                                              daemon=True, name='update')
                update_trd.start()
            ignore_update_by_init = False

            # wait for the next period
            sleep(check_period)

    def _update(self, update_list, callback_func, callback_threshold, ignore_update=False):
        # download with multi threads if the number of data is bigger than 1000.
        trd_list = []
        num_trd = min(len(update_list) // 1000, 7) + 1 # maximum number of threads is 8.

        # decision for whether to run callback or not
        if not ignore_update: self.num_update += len(update_list)
        run_callback = False
        if callback_func != None and callback_threshold != None:            # if callback is given
            if self.num_update >= callback_threshold:                       # if num_update is enough for callback
                run_callback = True
                self.num_update = 0
                callback_name = datetime.today().strftime("%Y%m%d%H%M%S")
                self.callback_in_progress.append(callback_name)

        # download start
        term = len(update_list) // num_trd + 1
        start_idx = 0
        end_idx = min(term, len(update_list))
        print(update_list, len(update_list))
        for idx in range(num_trd):
            print(start_idx, end_idx)
            trd_list.append(threading.Thread(target=self._download, args=(update_list[start_idx:end_idx],),
                                             daemon=True, name=f's3_download_#{idx}'))
            start_idx = end_idx
            end_idx = min(end_idx + term, len(update_list))
        for idx in range(num_trd):
            trd_list[idx].start()
        for idx in range(num_trd):
            trd_list[idx].join()

        # run callback after downloads are done
        if run_callback:
            # wait until the previous callback is done
            while self.callback_in_progress[0]!=callback_name:
                sleep(600)
            callback_func()
            self.callback_in_progress.pop(0)

    def _download(self, update_list):
        for obj_path in update_list:
            obj_name = obj_path.split('/')[-1]
            self.client.download_file(self.bucket, obj_path, self.local_dir + '/' + obj_name)

    def _dir_format(self, s3_dir, local_dir):
        # s3_dir format
        if s3_dir[-1]== '/':
            s3_dir = s3_dir
        else:
            s3_dir = s3_dir + '/'

        # local_dir format
        if len(local_dir) == 0: local_dir = 's3_sync_dir'
        if not '/'  in local_dir: local_dir = './' + local_dir
        local_dir = local_dir.split('/')
        if local_dir[0]=='.':
            local_dir.insert(0, os.getcwd())
        elif local_dir[0]=='':
            pass
        local_dir = '/'.join(local_dir)

        if local_dir[-1] != '/': local_dir = local_dir + '/'

        return s3_dir, local_dir

