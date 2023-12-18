# OAT artefact downloading 

Many OAT components require external artefacts to be retrieved from remote locations before they can run locally. This document describes how automatic artefact downloading is configured and implemented. 

## Configuration files

Downloads are configured for each individual OAT service through the various `<service name>/downloads.toml` files in the repository. 

Each of these defines a list of one or more download "sources", which in turn contain lists of one or more URLs indicating files to be downloaded. Each source also has a list of artefact IDs which are used by the components in the service to retrieve paths to the downloaded files that they require. 

A minimal example:

```toml
# service name
name = "offline"

# path where all files downloaded for the service will be placed under (note that this
# is a path in the context of the Docker container used by the service!)
base_path = "/shared/file_system/downloads/offline/"

# each "[[sources]]" entry defines a new download source, indicating a group of one or
# more related URLs to be downloaded
[[sources]]
# an identifier for this source
id = "extra_info_data_recent"

# a list of [URL, local name] pairs. The local name is appended to the base_path 
# to give the final path where the downloaded files will end up. e.g. here it will be
# "/shared/file_system/downloads/offline/extra_info_data"
urls = [
    ["s3://oat-2-data/offline/extra_info_data/recent/", "extra_info_data"],
   # "https://..." URLs can appear here too
]

# a list of [ID, filename] pairs. These artefact IDs are what the Python components will 
# use to retrieve the full local paths of the artefacts. The filenames are relative to 
# the base_path so they need to include the local path from the urls list. 
artefacts = [
    ["jokes_json", "extra_info_data/jokes_images.json"],
    ["facts_json", "extra_info_data/facts_images.json"],
]

# add more [[sources]] if required...
```

This file defines a single download source for the offline service which will copy a folder from an S3 bucket to a local path. It then defines 2 artefact IDs which reference specific files in the folder, so that their complete filenames can be retrieved by service components. 

For a more detailed example of a configuration, see the `downloads-template.toml` file in the root of the repository.

## Downloading files

Using the above example of a download configuration, a component wishing to download and open one of these artefacts would do the following:

```python
from utils import Downloader
...
# create a Downloader instance. When the constructor is called without
# parameters it uses the default filename of "downloads.toml"
downloader = Downloader()

# tell the Downloader to download all the sources required for a set of artefact IDs.
# Only the necessary sources are downloaded, any others defined in the configuration
# file will be ignored.
# If the files already exist locally then they will not be downloaded again.
downloader.downloader(["jokes_json", "facts_json"])

# now get the full local path to the jokes_images.json file
jokes_json_path = downloader.get_artefact_path("jokes_json")

# in this example this would print: 
#     "/shared/file_system/downloads/offline/extra_info_data/jokes_images.json"
print(jokes_json_path)
```

The `Downloader` class is implemented in `shared/utils/downloads.py`. It supports downloading from S3 buckets with local credentials as well as standard file downloading over HTTP. 

If an S3 URL is used, the command executed by the `Downloader` will be: `aws s3 cp <url> <download path> --recursive`. 

The `Downloader` can optionally decompress common types of compressed file after they are downloaded: `.zip`, `.tar.bz2`, `.tar.gz`, `.gz`, `.bz2`. This is enabled by default. To disable it, add a line `decompress = false` to the download source definition in the configuration file.

If a component wants direct access to the downloaded files instead of referencing them by artefact IDs, this is also supported:

```python
downloader = Downloader()
downloader.download() # this will just download all sources

# get the path to the directory where source abc files are located
abc_path = downloader.get_path("abc")

# wrapper for os.listdir(abc_path)
abc_files = downloader.list_contents("abc")
```
