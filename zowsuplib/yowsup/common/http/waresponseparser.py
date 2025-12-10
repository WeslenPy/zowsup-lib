import json
import logging
from loguru import logger

class ResponseParser(object):
    def __init__(self):
        self.meta = "*"
        
    def parse(self, text, pvars):
        return text
    
    def getMeta(self):
        return self.meta
    
    def getVars(self, pvars):
        if type(pvars) is dict:
            return pvars
        if type(pvars) is list:
            
            out = {}
            
            for p in pvars:
                out[p] = p
                
            return out



class JSONResponseParser(ResponseParser):
    
    def __init__(self):
        self.meta = "text/json"

    def parse(self, jsonData, pvars):
        
        d = json.loads(jsonData)
        pvars = self.getVars(pvars)

        parsed = {}     
        
        for k,v in pvars.items():
            parsed[k] = self.query(d, v)

        return parsed
    
    def query(self, d, key):
        keys = key.split('.', 1)
            
        currKey = keys[0]
        
        if(currKey in d):
            item = d[currKey]
            
            if len(keys) == 1:
                    return item
            
            if type(item) is dict:
                return self.query(item, keys[1])
            
            elif type(item) is list:
                output = []

                for i in item:
                    output.append(self.query(i, keys[1]))
                return output
            
            else:
                return None


        


