# -*- coding: utf-8 -*-

# Rate of updating file in seconds
global_update_rate = 30

updaters = [
    {
        'type': 'local',
        'path': 'status.json',
        # optional: inherits global_update_rate
        #           can be used for any updater
#        'update_rate': 10
    },
#    {
#        'type': 'ftp',
#        'server': 'example.com',
#        'port': 21, 
#        'username': 'anonymous',
#        'password': '',
#        'path': 'public_html/status.json'
#    }
]
