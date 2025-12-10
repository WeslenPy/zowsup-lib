class ParamsNotEnoughException(Exception):
    
    def __init__(self):        
        pass
    
    def getMsg(self):
        return "Params not enough"

