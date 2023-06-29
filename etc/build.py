from datetime import datetime
import yaml
from pathlib import Path
import os

info = Path(os.getenv("CONFIG"), "info.yml")
build_stamp = {"build_info": 'x', "build_version": 0.1}

with open(info, 'r+') as file:

    build_stamp["build_info"] = datetime.now()
    yaml.dump(build_stamp, file, default_flow_style=False)