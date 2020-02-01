from typing import Callable
import requests
import re

from pylaunch.ssdp import ST_ROKU, SimpleServiceDiscoveryProtocol
from pylaunch.xmlparse import XMLFile, normalize

class Application:
    def __init__(self, name, id, type, subtype, version, roku):
        self.name = name
        self.id = id
        self.type = type
        self.subtype = subtype
        self.version = version
        self.roku=roku

    def __repr__(self):
        return "{cn}(name='{name}', id='{id}', type='{type}', subtype='{subtype}', version='{version}')".format(
            cn = self.__class__.__name__,
            name = self.name,
            id = self.id,
            type = self.type,
            subtype = self.subtype,
            version = self.version
        )

    def __getattribute__(self, name):
        return super().__getattribute__(name)

    @property
    def icon(self):
        request_url = f'{self.roku.address}/query/icon/{self.id}'
        response = requests.get(request_url, stream=True)
        if str(response.headers['Content-Length']) != '0':
            filetype = response.headers['Content-Type'].split('/')[-1]
            return {'content': response.content, 'filetype': filetype}

    def launch(self, callback: Callable[[None], dict]=None, **kwargs) -> None:
        request_url = f'{self.roku.address}/launch/{self.id}'
        response = requests.post(
            request_url,
            params=kwargs,
            headers={'Content-Length':'0'}
        )
        if callback:
            results = {
                'request_url': request_url,
                'status_code': response.status_code
            }
            callback(results)

def discover(timeout=3) -> list:
    '''
    Scans the network for roku devices.
    '''
    results = []
    SimpleServiceDiscoveryProtocol.settimeout(timeout)
    ssdp = SimpleServiceDiscoveryProtocol(ST_ROKU)
    response = ssdp.broadcast()
    for resp in response:
        location = resp.headers.get('location')
        if not location:
            continue
        results.append(Roku(location))
    return results


class Roku:
    def __init__(self, address):
        self.bind(address)
        self.apps = self.query_apps()

    def __getitem__(self, prop):
        return self.__getattribute__(prop)

    def __enter__(self):
        self._session = requests.Session()
        return self

    def __exit__(self, *args):
        self._session.close()

    def __repr__(self):
        return f'{self.__class__.__name__}({self.address!r})'

    @property
    def request(self):
        try:
            return self._session
        except:
            return requests

    @property
    def active_app(self):
        request_url = f'{self.address}/query/active-app'
        response = self.request.get(request_url)
        xml = XMLFile(response.text)
        element = xml.find('app')
        return Application(
            name=element.text,
            id=element.attrib.get('id'),
            type=element.attrib.get('type'),
            subtype=element.attrib.get('subtype'),
            version=element.attrib.get('version'),
            roku=self
        )

    def bind(self, address) -> None:
        self.address = address
        request_url = f'{self.address}/query/device-info'
        response = self.request.get(request_url)
        xml = XMLFile(response.text)
        for element in xml.find('device-info'):
            key, value = normalize(xml, element)
            setattr(self, key, value)

    def query_apps(self) -> list:
        apps = {}
        request_url = f'{self.address}/query/apps'
        response = self.request.get(request_url)
        xml = XMLFile(response.text)
        for element in xml.find('apps'):
            app = Application(
                name=element.text,
                id=element.attrib.get('id'),
                type=element.attrib.get('type'),
                subtype=element.attrib.get('subtype'),
                version=element.attrib.get('version'),
                roku=self
            )
            apps[app.name] = app
        return apps

    def install(self, id:str, **kwargs) -> None:
        request_url = f'{self.address}/install/{str(id)}'
        response = self.request.post(
            request_url,
            params=kwargs,
            headers={'Content-Length':'0'}
        )

    def key_press(self, key: str, callback: Callable[[None], dict]=None) -> None:
        request_url = f'{self.address}/keypress/{str(key)}'
        response = self.request.post(request_url)
        if callback:
            results = {
                'request_url': request_url,
                'status_code': response.status_code
            }
            callback(results)
  
    def power(self):
        power_modes = {'PowerOn': 'Headless', 'Headless': 'PowerOn'}
        toggle_power_mode = lambda x: setattr(
            self, 'power_mode', power_modes[self.power_mode]
        ) if x['status_code'] == 200 else None

        self.key_press('power', toggle_power_mode)

if __name__ == '__main__':
    devices = discover()
    try:
        target = devices[0]
        print(target.address)
        print(target.power_mode)
        if target.power_mode == 'PowerOn':
            target.power()
        print(target.active_app)
            
    except IndexError:
        print("Didn't receive ip address before SSDP timeout.")


