# -*- coding: utf-8 -*-

import abc


class TaskMsgStore(object):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def setTaskMsg(self, msg_id,task_id,src,dst):
        pass

    @abc.abstractmethod
    def getTaskMsg(self,msg_id):
        pass

    @abc.abstractmethod
    def getMsgTaskByResponseMsg(self,sender,receive):
        pass

    @abc.abstractclassmethod
    def delExpiredTaskMsg(self):
        pass

