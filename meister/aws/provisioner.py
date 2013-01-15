'''
Created on Jan 10, 2013

@author: fabsor
'''
import ec2
from libcloud.compute.types import Provider
import time

class Provisioner:
    
    
    def __init__(self, connection, logger):
        self.connection = connection
        self.logger = logger
    
    def provisionSecurityGroups(self, groups):
        existingGroups = self.connection.getSecurityGroups()
        for name, group in groups.items():
            if not name in existingGroups:
                self.logger.log("Creating security group {0}".format(name))
                ec2Group = self.connection.createSecurityGroup(name, group["description"])
            else:
                ec2Group = existingGroups[name]
            for rule in group["rules"]:
                self.logger.log("Creating rule {0}:{1}-{2}".format(rule["ip"], rule["fromPort"], rule["toPort"]))
                ec2Group.addRule(rule["fromPort"], rule["toPort"], rule["ip"])

    def provisionNodes(self, nodes):
        # Find existing nodes.
        existingNodes = self.connection.getNodes()
        elasticIps = self.connection.getElasticIPs(False)
        for name, node in nodes.items():
            # Create non-existing nodes.
            if not name in existingNodes:
                self.logger.log("Creating node {0}".format(name))
                createdNode = self.connection.createNode(node.image, node.size, name, node.diskSize, node.securityGroup, node.zone, node.keyName)
            else:
                self.logger.log("Node {0} already exists.".format(name))

    def deleteNodes(self, nodes):
        """
        Terminate all nodes from a configuration.
        """
        existingNodes = self.connection.getNodes()
        for name in nodes.keys():
            if name in existingNodes:
                self.logger.log("Deleting node {0}".format(name))
                existingNodes[name].destroy()
    
    def createElasticIps(self, nodes):
        # Associate elastic IP addresses.
        existingNodes = self.connection.getNodes(True)
        elasticIps = self.connection.getElasticIPs(False)
        for name, node in nodes.items():
            if nodes[name].elasticIP and existingNodes[name].public_ip[0] not in elasticIps:
                self.logger.log("Creating elastic IP for {0}".format(name))
                if len(elasticIps):
                    elasticIp = elasticIps.pop()
                else:
                    self.logger.log("Allocating new IP address")
                    elasticIp = self.connection.allocateElasticIP()
                
                self.logger.log("Using IP {0}".format(elasticIp))
                self.connection.associateIP(existingNodes[name], elasticIp)
                nodes[name].externalIp = elasticIp
                while existingNodes[name].public_ip[0] != elasticIp:
                    existingNodes = self.connection.getNodes(True)
                    time.sleep(2)

    def deleteSecurityGroups(self, groups):
        existingGroups = self.connection.getSecurityGroups()
        for name in groups.keys():
            if name in existingGroups:
                self.logger.log("Deleting security group {0}".format(name))
                self.connection.deleteSecurityGroup(name)

    def verify(self, nodes, wait=10, waiting = False):
        """
        Verify changes by waiting until the servers are done 
        """
        existingNodes = self.connection.getNodes(True)

        for name in nodes.keys():
            if name in existingNodes:
                if existingNodes[name].extra['status'] != "running" or not len(existingNodes[name].public_ips):
                    self.logger.log("Node {0} is not ready. Waiting for {1} seconds.".format(name, wait))
                    time.sleep(wait)
                    return self.verify(nodes, wait, True)
                else:
                    self.logger.log("Node {0} is running".format(name))
                    nodes[name].externalIp = existingNodes[name].public_ip[0]
                    nodes[name].internalIp = existingNodes[name].private_ip[0]
        if waiting:
            # Wait some more, machines usually needs a bit more time to get really ready.
            time.sleep(wait)
