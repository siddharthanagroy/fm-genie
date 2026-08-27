import sys

print("Python:", sys.version)

import google
print("google:", google)
print("google path:", list(google.__path__))

import google.cloud
print("google.cloud:", google.cloud)
print("google.cloud path:", list(google.cloud.__path__))

from google.cloud import firestore
print("firestore:", firestore)
print("firestore file:", firestore.__file__)

print("SUCCESS")
