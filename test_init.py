#!/usr/bin/env python
import sys
import logging
logging.basicConfig(level=logging.DEBUG, format='%(levelname)s - %(name)s - %(message)s')
sys.path.insert(0, '/home/dhyan/feature-flagging')

from index import app
print("App loaded successfully")
print(f"Routes: {len(app.url_map._rules)}")
