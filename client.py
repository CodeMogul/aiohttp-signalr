import asyncio
import aiohttp
import json
import urllib.parse as parse
import functools
from enum import Enum

def buildPayload(hub_name, method_name, args, message_id):
    data = {
        'H': hub_name,
        'M': method_name,
        'A': args,
        'I': message_id
    }
    return json.dumps(data)

def getCleanedHubs(hub_names):
    ret = []
    if len(hub_names):
        for hub in hub_names:
            if isinstance(hub, str):
                ret.append({"name": hub.lower()})
    return ret

class ConnectionCodes(Enum):
    UNBOUND = 1
    BOUND = 2
    CONNECTING = 3
    CONNECTED = 4
    DISCONNECTING = 5
    DISCONNECTED = 6
    FAILED = 7
    ERROR = 8
    BINDING_ERROR = 9
    RETRYING = 10
    RETRY_FAILED = 11

class Client:
    def __init__(self, base_url, hub_list, headers=None):
        cleaned_hubs = getCleanedHubs(hub_list)
        if len(cleaned_hubs) == 0:
            raise Exception('Error: You must define atleast one hub and of type str')
        url_frags = parse.urlparse(base_url)
        if url_frags.scheme not in ('ws', 'wss', 'http', 'https'):
            raise Exception('InvalidSchemeError:')
        
        if url_frags.scheme == 'ws':
            url_frags = url_frags._replace(scheme='http')
        elif url_frags.scheme == 'wss':
            url_frags = url_frags._replace(scheme='https')

        self._url = url_frags.geturl()
        self._hub_data = cleaned_hubs
        self._proxies = {}
        self._headers = {} if headers is None else headers
        self._query_params = {}
        self._connection = {
            "state": ConnectionCodes.UNBOUND,
            "token": '',
            "id": '',
            "messageId": 0
        }
        self._timeouts = {
            "keepAlive": 0,
            "disconnect": 0,
            "connect": 0
        }
        self._hubs = []
        self._websocket = None
        self._session = aiohttp.ClientSession(headers=self._headers)

    async def _negotiate(self):
        # Add client headers and proxy
        proxies = {}
        headers = {}

        negotiate_url = self._getNegotiateUrl()
        # getRequest = functools.partial(requests.get, params=params, headers=headers, proxies=proxies)
        try:
                res = await self._session.get(negotiate_url)
                # res = requests.get(negotiate_url, headers=headers, proxies=proxies)
        except Exception as e:
            # set client status binding error and call service handler
            raise e

        # Res contains:
        # Url	                    "/signalr"	        str
        # ProtocolVersion	        "1.2"	            str
        # TryWebSockets	            true	            bool
        # ConnectionToken	        "..."	            str
        # ConnectionId	            "..."	            str
        # KeepAliveTimeout	        20.0	            float
        # DisconnectTimeout	        30.0	            float
        # TransportConnectTimeout	5.0	                float

        try:
            if res.status == 200:
                negotiated_vals = await res.json()
                if not negotiated_vals["TryWebSockets"]:
                    # raise error This client only supports websockets
                    raise Exception('WebSocketsError: This client does not support websockets')
                else:
                    bindings = {
                        "url": self._url,
                        "connection": {
                            "token": negotiated_vals["ConnectionToken"],
                            "id": negotiated_vals["ConnectionId"]
                        },
                        "timeouts": {
                            "keepAlive": negotiated_vals["KeepAliveTimeout"],
                            "disconnect": negotiated_vals["DisconnectTimeout"],
                            "connect": negotiated_vals["TransportConnectTimeout"]
                        }
                    }
            elif res.status == 401 or res.status == 302:
                # call client unauthorised handler with res param
                raise Exception("AuthError occured while Negotiation")
            else:
                raise Exception("Unknown HTTP Response Code recieved while Negotiation")
        except Exception as e:
            raise e
        
        return bindings

    def _getNegotiateUrl(self):
        qs = {
            "connectionData": json.dumps(self._hub_data),
            "clientProtocol": 1.5
        }

        # Add user query_params
        negotiate_url = self._url + '/negotiate?' + parse.urlencode(qs)
        return negotiate_url

    def _getConnectUrl(self):
        qs = {
            "clientProtocol": 1.5,
            "transport": "webSockets",
            "connectionToken": self._connection["token"],
            "connectionData": json.dumps(self._hub_data),
            "tid": 10
        }

        url_frags = parse.urlparse(self._url)
        schm = 'wss' if url_frags.scheme == 'https' else 'ws'
        url_frags = url_frags._replace(scheme=schm)
        # Add user query_params
        connect_url = url_frags.geturl() + '/connect?' + parse.urlencode(qs)
        return connect_url
    
    def _getStartUrl(self):
        qs = {
            "clientProtocol": 1.5,
            "transport": "webSockets",
            "connectionToken": self._connection["token"],
            "connectionData": json.dumps(self._hub_data),
        }

        # Add user query_params
        start_url = self._url + '/start?' + parse.urlencode(qs)
        return start_url

    async def start(self):
        # check connnection states before doing anything
        bindings = await self._negotiate()
        self._timeouts.update(bindings['timeouts'])
        self._connection.update(bindings['connection'])

        connect_url = self._getConnectUrl()

        self._websocket = await self._session.ws_connect(connect_url)
        print(dir(self._websocket))
        print('\n\n')

        # Notify server of start
        # Check start sequence
        # res = await self._websocket.recv():
        #     if 
        start_url = self._getStartUrl()
        res = await self._session.get(start_url)
        if res.status == 200:
            print(res.text)
            print('\n\n')

    async def invoke(self, hub_name, function, *args):
        if self._websocket is None:
            raise Exception("Invoke called before Connection Initiation")
        self._connection["messageId"] += 1
        m_id = self._connection["messageId"]
        payload = buildPayload(hub_name.lower(), function, args, m_id)
        await self._websocket.send_str(payload)
        message = await self._websocket.receive_str()
        print("Command {} sent: Res {}".format(function, message))

    async def recv(self):
        if self._websocket is None:
            raise Exception("Recieve called before Connection Initiation")
        message = await self._websocket.receive()
        # if msg.type == aiohttp.WSMsgType.TEXT:

        return message.data

    async def disconnect(self):
        # Reset connection Ids and tokens etc
        await self._websocket.close()
        self._session.close()