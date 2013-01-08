'''
Created on Nov 22, 2012

@author: fabsor
'''
import httplib
from hashlib import sha1
import hmac
from base64 import b64encode
import xml.etree.ElementTree as ET 

class Route53Connection:
    ROUTE53_ENDPOINT = "route53.amazonaws.com"
    ROUTE53_API = "2012-02-29"
    
    def __init__(self, id, key):
        self.id = id
        self.key = key
        self.path = "/{0}/".format(self.ROUTE53_API);
        conn = httplib.HTTPSConnection(self.ROUTE53_ENDPOINT);
        conn.request('get', "/date");
        response = conn.getresponse()
        self.date = response.getheader("Date", False)
        auth = hmac.new(key, self.date, sha1)
        self.token = b64encode(auth.digest())
        self.headers = {
            "Date": self.date,
            'X-Amzn-Authorization': "AWS3-HTTPS AWSAccessKeyId={0},Algorithm=HmacSHA1,Signature={1}".format(id, self.token)
        }
        print self.headers
        
    def saveZone(self, zone):
        """
        Save a zone to route 53.
        @param name
            The name of the domain, for example example.com.
        @param comment
            A comment about this zone.
        """
        identifier = "request-create-{0}-{1}".format(zone.name, self.date)
        request = '''<?xml version="1.0" encoding="UTF-8"?>
        <CreateHostedZoneRequest xmlns="https://route53.amazonaws.com/doc/2012-02-29/">
           <Name>{0}</Name>
           <CallerReference>{1}</CallerReference>
           <HostedZoneConfig>
              <Comment>{2}</Comment>
           </HostedZoneConfig>
           </CreateHostedZoneRequest>'''.format(zone.name, identifier, zone.comment)
        conn = httplib.HTTPSConnection(self.ROUTE53_ENDPOINT)
        conn.request("POST", self.path + "/hostedzone", request, self.headers)
        response = conn.getresponse()
        result = response.read()
        conn.close()
        return self.zoneFromResponse(result)
        
    def deleteZone(self, zone):
        conn = httplib.HTTPSConnection(self.ROUTE53_ENDPOINT)
        conn.request("DELETE", self.path + zone.id, '', self.headers)
        conn.close()
        
    def getZones(self, limit=100):
        """
        Get a list of zones.
        @param limit
            The limit of items to return
        @return: 
            Zone[] an array of Zone objects.
        @todo Make sure we can support more domains than 100.
        """
        conn = httplib.HTTPSConnection(self.ROUTE53_ENDPOINT)
        conn.request("GET", self.path + "/hostedzone?maxitems={0}".format(limit), '', self.headers)
        response = conn.getresponse().read()
        return self.zonesFromResponse(response)
        
    def zonesFromResponse(self, result):
        """
        Convert a response from rotue 53 to a Zone object.
        @param result
        @return: Zone
        """
        root = ET.fromstring(result) 
        zoneObjects = []
        for zone in root.findall("./{0}/{1}".format(self.getTagName('HostedZones'), self.getTagName('HostedZone'))):
            zoneObjects.append(self.zoneFromResponse(zone))
        return zoneObjects
        
    def zoneFromResponse(self, result):
        """
        Create a Zone object from an AWS response.
        @param result: A createdZoneResonse from AWS.  
        """
        root = ET.fromstring(result) if not isinstance(result, ET.Element) else result
        zone = root if root.tag == self.getTagName("HostedZone") else root.find(self.getTagName("HostedZone"))
        # Basic info
        zoneObj = Zone(
                       name=zone.find(self.getTagName("Name")).text,
                       callerReference=zone.find(self.getTagName("CallerReference")).text,
                       id=zone.find(self.getTagName("Id")).text,
                       )
        comment = zone.find("./{0}/{1}".format(self.getTagName("Config"), self.getTagName("Comment")))
        if comment is not None:
            zoneObj.comment = comment.text
        servers = root.findall('./{0}/{1}/{2}'.format(self.getTagName("DelegationSet"), self.getTagName("NameServers"), self.getTagName("NameServer")))
        for server in servers:
            zoneObj.addNameServer(server.text)
        return zoneObj

    def getTagName(self, name):
        return "{https://route53.amazonaws.com/doc/2012-02-29/}" + name
       

   
class Zone:
    """
    The Zone object describes a zone.
    """
    def __init__(self, name, comment = '', callerReference = None, id = None):
        self.id = id
        self.name = name
        self.callerReference = callerReference
        self.comment = comment
        self.nameservers = []
        
    def addNameServer(self, name):
        self.nameservers.append(name)