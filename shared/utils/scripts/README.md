# OAT Scripts

The `shared/utils/scripts` folder contains scripts for extracting sessions, search logs and ASR logs from the database. 

See below for more information and how to run the scripts. 

### download_sessions.py
The download sessions script is currently configured to only extract logs from the local client. To run the script, first install the required dependencies: 
```
pip install -r /path/to/OAT/oat_common/requirements.txt
```
Then navigate to the directory and run the script:
```
cd path/to/OAT/shared/utils/scripts
python3 download_sessions.py
```
The sessions will be saved in the `shared/utils/scripts` folder in a file named `sessions_dump.json`.
