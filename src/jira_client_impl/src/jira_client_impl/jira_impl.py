"""
Jira Client Implementation:

This is some boiler plate code for the concrete implementation of the work_mgmt_client interface for Jira.

"""


import logging
import os
import work_mgmt_client_interface

class JiraClient(work_mgmt_client_interface.Client):
    """
    Concrete implementation if the Client abstraction using Jira API..
    """
    def auth():
        #ToDo: implement authentication methods using OAuth 2.0 (3LO) 
        return None
    
    def get_issue(self, issue_key: str) -> Issue:
        #ToDo: implement
        return None
    
    def update_issue(self, issue_key: str, title = None):
        #ToDo: implement
        return None
    

def get_client(*, interactive: bool = False) -> Client:
        #ToDo: implement
        return None

