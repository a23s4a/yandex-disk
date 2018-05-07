import gnupg
import os
from urllib.parse import urlencode
import requests
# from requests_toolbelt import MultipartEncoder
client_id = '103cdd041bfb4b7b9ae5db4189619d61'
client_secret = '60177c86bdfc4ebfa4b005ce780a4586'
base_auth_url = 'https://oauth.yandex.ru/'

device_id = 'yadi_sk'
device_name = 'openbsd'
force_confirm = 'yes'
state = '1234567890'

ya_token = 'ya_token'

disk_root = '/mnt/'


def which(prg):
    from subprocess import check_output, CalledProcessError
    try:
        return check_output(['which', prg]).decode().strip()
    except CalledProcessError:
        return False


gpgbinary = which('gpg2')
gpg = gnupg.GPG(gpgbinary=gpgbinary)
gpg.encoding = 'utf-8'
gpg_fp = gpg.list_keys(True)[0]['fingerprint']


class Yadi():
    def __init__(self):
        def current_token():
            if os.path.exists(ya_token):
                with open(ya_token) as f:
                    encr_token = f.read()
                    if encr_token:
                        token = str(gpg.decrypt(encr_token))
                        return token
                    else:
                        return False
            else:
                return False
        self.token = current_token() or self.login()

    def login(self):
        self.login = input('Введите Ваш логин от служб Яндекса: ')
        yandex_base_url = 'https://oauth.yandex.ru/authorize?'
        data = {
            'response_type': 'code',
            'client_id': client_id,
            'device_id': device_id,
            'device_name': device_name,
            'login_hint': self.login,
            'force_confirm': force_confirm,
            'state': state
        }
        data = urlencode(data)
        oauth_url = yandex_base_url + data
        print('Перейдите по ссылке и подтвердите '
              'доступ приложения к Вашему диску\n',
              oauth_url)

        response_code = input('Введите код авторизации, '
                              'полученный при подтверждении доступа: ')

        data = {
            'grant_type': 'authorization_code',
            'code': response_code,
            'client_id': client_id,
            'client_secret': client_secret
        }
        data = urlencode(data)
        answer = requests.post(base_auth_url + 'token', data)
        token = answer.json()['access_token']
        encr_token = str(gpg.encrypt(token, gpg_fp))
        with open(ya_token, 'w') as yt:
            yt.write(encr_token)
            return token

    def disk_info(self):
        headers = {'Authorization': 'OAuth' + ' ' + self.token}
        disk = 'https://cloud-api.yandex.net/v1/disk/'
        answer = requests.get(disk, headers=headers)
        return answer.json()

    def search_resources(self,
                         resource_name='',
                         limit=20,
                         media_type='',
                         path='',
                         ):
        base_url = 'https://cloud-api.yandex.net/v1/disk/resources?'
        data = {
            'path': 'app:/' + path,
            'limit': limit,
            'media_type': media_type,
        }
        data = urlencode(data)
        headers = {'Authorization': 'OAuth' + ' ' + self.token}
        url = base_url + data
        answer = requests.get(url, headers=headers)
        return answer.json()

    def list_folders(self):
        base_url = 'https://cloud-api.yandex.net/v1/disk/resources?'
        data = {
            'path': 'app:/',
        }
        data = urlencode(data)
        headers = {'Authorization': 'OAuth' + ' ' + self.token}
        url = base_url + data
        answer = requests.get(url, headers=headers)
        return answer.json()

    def upload_file(self, filepath, overwrite=False):
        filename = os.path.basename(filepath)
        if overwrite:
            o = 'true'
        else:
            o = 'false'
        base_url = 'https://cloud-api.yandex.net/v1/disk/resources/upload?'
        data = {
            'path': 'app:/' + filename,
            'overwrite': o,
        }
        data = urlencode(data)
        headers = {'Authorization': 'OAuth' + ' ' + self.token}
        url = base_url + data
        answer = requests.get(url, headers=headers)
        if answer.ok:
            upload_url = answer.json()['href']
            with open(filepath, 'rb') as f:
                result = requests.put(upload_url, data=f)
                return result
        else:
            print(answer.json())
            print('Ошибка')

    def download_file(self, filename, dst_file_path=disk_root):
        base_url = 'https://cloud-api.yandex.net/v1/disk/resources/download?'
        data = {
            'path': 'app:/' + filename,
        }
        headers = {'Authorization': 'OAuth' + ' ' + self.token}
        data = urlencode(data)
        url = base_url + data
        answer = requests.get(url, headers=headers)
        if answer.ok:
            download_url = answer.json()['href']
            dst_file_full_path = dst_file_path + '___' + filename
            result = requests.get(download_url, stream=True)
            with open(dst_file_full_path, 'wb') as fo:
                for chunk in result.iter_content(2000):
                    fo.write(chunk)
        else:
            print(answer.json())
            print('Ошибка')
