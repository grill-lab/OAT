# Downloader service

The OAT services which currently need to download external artefacts before running are:
 * `offline`
 * `functionalities`
 * `neural_functionalities`
 * `llm_functionalities`

They are configured so that the necessary downloads will normally be performed when the services are first started and the files only need to be downloaded once. See [README-downloads.md](../doc/README-downloads.md) for more information on this functionality.

However if you want to pre-download all the files for any reason, or are testing downloading of new files, it might be simpler to trigger the downloads through this service instead:

```shell
docker compose build downloader
# trigger all downloads for these 2 services
docker compose run downloader offline functionalities
```

To add other services, edit `docker-compose.yml` and add a new volume mount for the `OAT/<service name>` path at `/<service_name>`.
