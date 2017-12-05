import os
import json
import time
import contextlib
import sys
import re
import shutil
from tempfile import gettempdir
import importlib
import urllib.request
import zipfile
import glob
import requests
import io
from pathlib import Path

@contextlib.contextmanager
def stdout_redirect(where):
    old_stdout = sys.stdout
    sys.stdout = where
    try:
        yield where
    finally:
        sys.stdout = old_stdout

if __name__ == "__main__":

    tmp_location = Path(gettempdir()) / "RLUnit_worker"
    os.makedirs(tmp_location, exist_ok=True)
        
    process_another_experiment = True
    while process_another_experiment:
        try:
            r = requests.post("http://nginx:5000/queue/next")
        except requests.exceptions.ConnectionError:
            r = requests.post("http://127.0.0.1:5000/queue/next")
            
        trial_idx, agent_name, url = json.loads(r.text)
        
        if agent_name == "no work":
            time.sleep(3)
        else:

            # dynamically load the agent
            try: # download the agent
                _, file_name = os.path.split(url)
                tmp_agent = tmp_location/file_name
                urllib.request.urlretrieve(url, tmp_agent)
            except:
                raise Exception("Could not download the file for some reason.")

            try: # loading the specs if present
                spec = importlib.util.spec_from_file_location("agent",
                                                              tmp_agent)
                agent = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(agent)
            except ModuleNotFoundError as e:
                raise
            except:
                raise Exception("Could not load the file.")

            spec = agent.spec
            if "trial_func" in spec:
                train_function_name = spec["trial_func"]
            elif hasattr(agent,"run_trial"):
                train_function_name = "run_trial"
            elif hasattr(agent,"main"):
                train_function_name = "main"
            else:
                raise Exception("Unable to find training function in %s" % url)
            train_function = getattr(agent, train_function_name)

            data_location = tmp_location
            data_location /= agent_name
            data_location /= str(trial_idx)
            os.makedirs(data_location, exist_ok=True)
            
            with open(data_location/"stdout.log","w+") as stdout_log:
                with stdout_redirect(stdout_log):
                    try:
                        train_function(trial_idx)
                    except RuntimeError as e:
                        print("An error has occurred while running %s" %
                              agent_name)
                        print(e)
                    
            try:
                saved_files = spec["saved_files"]
            except KeyError:
                print("Agent %s doesn't seem to specify any files to save."
                      % agent_name)
                saved_files = []

            for file in saved_files:
                result = re.search("(.\w+)$",file)
                if result.group(1):
                    extension=result[1]
                else:
                    print("File %s doesn't have a valid extension" % file)
                    continue

                if (extension == ".jpg" or extension == ".jpeg"
                    or extension == ".png"):
                    os.makedirs(data_location/"images", exist_ok=True)
                    copyfile(file, data_location/"images")
                elif extension == ".mp4":
                    os.makedirs(data_location/"videos", exist_ok=True)
                    copyfile(file, data_location/"videos")
                elif extension == ".npy":
                    location = data_location/"raw"
                    os.makedirs(location, exist_ok=True)
                    shutil.copy(file, location)

            archive_name = "%s.%d.zip" % (agent_name, trial_idx)
            archive_regex = re.compile("(%s[\\\/]%d[\\\/](?:\w+[\\\/])*\w+\.\w+)$"
                                       % (agent_name, trial_idx))
            with zipfile.ZipFile(tmp_location / archive_name, 'w',
                                 zipfile.ZIP_DEFLATED) as zip_file:
                for file in data_location.glob('**/*'):
                    result = archive_regex.search(str(file))
                    if result and result.group(1):
                        file_name = result.group(1)
                        zip_file.write(file, file_name)

            with open(tmp_location / archive_name, "rb") as archive_binary:
                zip_content = archive_binary.read()
                query_address = ("http://nginx:5000/results/agent/%s/%d" %
                        (agent_name, trial_idx))
                query_address_fallback = ("http://127.0.0.1:5003/results/agent/%s/%d" %
                        (agent_name, trial_idx))
                
                payload = {
                        "results":(archive_name, zip_content, 'application/zip')
                    }
                try:
                    r = requests.put(query_address, files=payload)
                except requests.exceptions.ConnectionError:
                    r = requests.put(query_address_fallback,
                                     files=payload)
