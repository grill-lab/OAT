# OAT package dependencies

This document briefly describes how to add or update OAT dependencies to keep package versions consistent across all the services.

## Adding or updating Python packages

Currently there is a small collection of packages installed as part of the `oat_common` image. Since most of the other service images are based on `oat_common`, you shouldn't need to list these packages in any other requirements.txt files. The current set of packages and versions installed in `oat_common` are listed [here](oat_common/requirements.txt).

New packages can either be added to `oat_common` (if it's likely to be used by most/all of the other services) or to 1 or more of the individual services if that's more appropriate. 

Before adding a new package you can use [this small script](shared/utils/check_deps/check_deps.py) to quickly check the current state of the repository. By default it will check all `requirements.txt` files for duplicated package entries with mismatched versions, but you can also use it to check if a package appears anywhere in any `requirements.txt` file. 

### Example: checking if a package already exists in OAT

Say you want to add the package `foo` to the service you're working on. The first thing to do is check if the package is already used elsewhere in the repo:

```bash
python utils/check_deps.py -f foo
# example output for: python utils/check_deps.py -f grpcio
grpcio found in oat_common: grpcio==1.47.0
```

If this doesn't find any results, you can just add a new entry to the appropriate `requirements.txt` file with a pinned version. If it *does* find a result, you can either use the same version, or if that is not possible then bump the existing version to match the version you want to use. 

### Example: checking if there are any mismatched package versions

If you want to verify that there are no mismatched package versions in any of the various `requirements.txt` files, you can run the script without any parameters:

```bash
python utils/check_deps.py

# example output when something is wrong
Found 1 package problems

foo
   - dashboard has version 1.2.3
   - functionalities has version 1.2.4
   - oat_common has version 1.3.4
```

## Adding or updating system packages

The `oat_common` image installs a limited set of common packages through `apt-get` which should be available in all dependent services. These are listed in the [Dockerfile](oat_common/Dockerfile). 
