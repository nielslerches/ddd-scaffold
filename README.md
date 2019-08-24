# ddd-scaffold

(WIP) Example of how one can structure a project in a somewhat clean way.

## Features
1. (punq)[https://github.com/bobthemighty/punq] for injecting dependencies (usually implementations of certain interfaces)
2. Easily and quickly testable business logic with an included script.
3. Uses a modified version of my own library (common-query)[https://github.com/nielslerches/common-query] for querying a repository
4.1. Included test uses an in-memory repository implementation for speed.

## Getting started
```bash
wget -o ./ddd-scaffold-master.zip https://github.com/nielslerches/ddd-scaffold/archive/master.zip
unzip ddd-scaffold-master.zip && ddd-scaffold-master.zip
mv ddd-scaffold-master <project name>
cd <project name>
python3 -mvenv .venv
. .venv/bin/activate
pip install -r requirements.txt #punq==0.3.0
./run.py unittests
```
