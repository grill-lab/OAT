# Utility scriots

## check_deps.py

This script is intended to assist in keeping Python package versions consistent across the set of services that are contained in the OAT repo.

If you run it without arguments as `python utils/check_deps.py` it will scan through the `requirements.txt` files for each service, and list 2 types of potential problems:

 * packages which are not pinned to a specific version
 * packages which are pinned to different versions in different services

It can also be used as a quick way to check if a given package is used in any of the services: `python utils/check_deps.py -f somepackage` will show any `requirements.txt` entries from any service matching that package name. 
