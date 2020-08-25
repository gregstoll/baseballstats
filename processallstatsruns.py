#!/usr/bin/python3
import os
import re
import subprocess

def run(args, output_file_name):
    with open(output_file_name, 'w') as output_file:
        subprocess.run(args, check=True, universal_newlines=True, stdout=output_file)

run(['./processstatsruns.py', 'runsperinningstats'], 'runsperinning.xml')
run(['./processballsstrikesstatsruns.py', 'runsperinningballsstrikesstats'], 'runsperinningballsstrikes.xml')
try:
    os.mkdir('statsruns')
except FileExistsError:
    # directory already exists
    pass
file_name_re = re.compile('runsperinningstatscumulative\.(\d+)')
file_name_balls_strikes_re = re.compile('runsperinningballsstrikesstatscumulative\.(\d+)')
stats_years_dir = os.path.abspath('statsyears')
for file_name in os.listdir(stats_years_dir):
    match = file_name_re.match(file_name)
    if match:
        year = match.group(1)
        output_file_name = os.path.join(os.path.abspath('statsruns'), 'runsperinningcumulative' + year + '.xml')
        run(['./processstatsruns.py', os.path.join(os.path.abspath('statsyears'), file_name)], output_file_name)
        print(year)
    balls_strikes_match = file_name_balls_strikes_re.match(file_name)
    if balls_strikes_match:
        year = balls_strikes_match.group(1)
        output_file_name = os.path.join(os.path.abspath('statsruns'), 'runsperinningballsstrikescumulative' + year + '.xml')
        run(['./processballsstrikesstatsruns.py', os.path.join(os.path.abspath('statsyears'), file_name)], output_file_name)
        print(year)
