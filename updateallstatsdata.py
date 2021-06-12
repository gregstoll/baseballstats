#!/usr/bin/python3
import os
import subprocess
import datetime

def friendly_time():
    return datetime.datetime.now().strftime('%X')

def run_python(args):
    print("------ " + friendly_time() + " RUNNING " + ' '.join(args))
    subprocess.run(['python3'] + args, check=True, universal_newlines=True)

def run_python_with_output(args, output_file_name):
    print("------ " + friendly_time() + " RUNNING " + ' '.join(args))
    with open(output_file_name, 'w') as output_file:
        subprocess.run(['python3'] + args, check=True, universal_newlines=True, stdout=output_file)

def run_rust(args):
    os.chdir("retrosheet_stats")
    all_args = ['cargo', 'run', '--release', '--', '-q'] + args
    print("------ " + friendly_time() + " RUNNING " + ' '.join(all_args))
    subprocess.run(all_args, check=True, universal_newlines=True)
    os.chdir("..")

run_rust([])
run_rust(['-r', 'StatsWithBallsStrikes'])
run_rust(['-y'])
run_rust(['-y', '-r', 'StatsWithBallsStrikes'])

run_python(['processcumulativestats.py', 'statsyears', '-q'])
run_python(['processcumulativeballsstrikesstats.py', 'statsyears', '-q'])
run_python(['processcumulativeballsstrikesrunsperinningstats.py', 'statsyears', '-q'])
run_python(['processcumulativerunsperinningstats.py', 'statsyears', '-q'])
run_python(['processleveragefromcumulative.py'])
run_python_with_output(['processstats.py', 'stats'], 'probs.txt')
run_python_with_output(['processballsstrikesstats.py', 'statswithballsstrikes'], 'probswithballsstrikes.txt')
run_python(['processallstatsruns.py'])
run_python_with_output(['processballsstrikesstatsruns.py', 'runsperinningballsstrikesstats'], 'runsperinningballsstrikes.xml')

