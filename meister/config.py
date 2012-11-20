'''

@author: fabsor
'''
from os.path import isfile
import yaml
from meister import aws

class Config:
    def getNodes(self):
        return self.nodes

    def getDriver(self):
        return self.driver

class YamlConfig(Config):
    '''
    Parses and makes configuration accessible.
    '''
    def __init__(self, configFile):
        '''
        
        '''
        self.configFile = configFile
        self.parse()
    
    def parse(self):
        data = yaml.load(open(self.configFile).read())
        self.driver = globals()[data['driver']['name']](data['driver'])
        self.nodes = {}
        for name, node in data["nodes"].items():
            self.nodes[name] = self.driver.getNode(name, node)

class AWSDriver:
    def __init__(self, settings):
        self.aws_id = settings['id']
        self.aws_key = settings['key']
        self.aws_region = settings['region']
        self.defaultSecurityGroup = settings['defaultSecurityGroup']

    def getConnection(self):
        aws.AWSConnection(self.aws_region, self.aws_id, self.aws_key) 

    def getNode(self, name, definition):
        if not 'securityGroup' in definition:
            definition['securityGroup'] = self.defaultSecurityGroup 
        return AWSNode(name, definition)

class Node:
    def __init__(self, name, definition):
        self.name = name
        self.hostname = definition['hostname']
        for prop in ["externalDNS", "internalDNS"]:
            if prop in definition:
                setattr(self, name, definition[prop])

class AWSNode(Node):
    def __init__(self, name, definition):
        Node.__init__(self, name, definition)
        for prop in ['image', 'securityGroup', 'size']:
            setattr(self, prop, definition[prop])
