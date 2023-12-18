# Theme uploader

The scripts in this folder can be used to push new themes to the themes database used by the system. 

The `build_themes.py` script will generate a JSON file containing Taskgraphs that have been matched to themes, and can optionally push them to the themes database in the local dynamodb instance. 

The script needs to be run as a component in the offline pipeline: enable the `ThemeBuilder` component in `offline/config.py` and then run the pipeline. Note that it depends on the system index files already existing, so you must have run the earlier stages of the pipeline before running this component. 

The component will output a file called `themes.json` to this folder. If the `upload_themes` parameter is set to `True`, the theme data is also pushed to the themes database used by the online system, currently called `Undefined_ThemeResults`.

We add a mapping as well from query to theme query in `Curated_ThemeMapping`.

## Details

TODO
