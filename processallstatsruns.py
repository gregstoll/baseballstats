#!/usr/bin/python3
import os
import re
import subprocess

def run(args, output_file_name):
    with open(output_file_name, 'w') as output_file:
        subprocess.run(args, check=True, universal_newlines=True, stdout=output_file)

run(['./processstatsruns.py', 'runsperinningstats'], 'runsperinning.xml')
try:
    os.mkdir('statsruns')
except FileExistsError:
    # directory already exists
    pass
file_name_re = re.compile('runsperinningstatscumulative\.(\d+)')
stats_years_dir = os.path.abspath('statsyears')
for file_name in os.listdir(stats_years_dir):
    match = file_name_re.match(file_name)
    if match:
        output_file_name = os.path.join(os.path.abspath('statsruns'), 'runsperinningcumulative' + match.group(1) + '.xml')
        run(['./processstatsruns.py', os.path.join(os.path.abspath('statsyears'), file_name)], output_file_name)
        print(match.group(1))
