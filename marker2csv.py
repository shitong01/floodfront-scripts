#!/usr/bin/env python
import os
from time import gmtime, strftime
import datetime
import csv
import pg8000 as pg
import sqlite3 as sqlite
import re
import argparse
import sys
import configparser as conf
from django.conf import settings

config = conf.ConfigParser()
config.read('config.ini')
if 'floodfront' not in config:
    sys.stderr.write('Config not configured.')
    exit(1)

# Required for django.conf to find settings module of project
sys.path.insert(0, config['floodfront']['ProjectPath'])
os.environ['DJANGO_SETTINGS_MODULE'] = 'serverfloodfront.settings'
db_username = config['floodfront']['User']
db_connection_name = config['floodfront']['Database']

# Print only in tty mode.
def tty_print(msg):
    if sys.stdout.isatty():
        print(msg)

def main():
    """
    Main function
    """

    parser = argparse.ArgumentParser(description=""" Export FloodFront marker data into CSV format. """)
    parser.add_argument('--since', type=str, help=""" Narrow selection to markers after this date. YYYY-MM-DD """)
    parser.add_argument('-o', '--output', type=str, help=""" File output name. """)

    args = parser.parse_args()
    if (args.since is not None) and (re.search("^[0-9]{4}-[0-9]{2}-[0-9]{2}$", args.since) is None):
        raise ValueError("Invalid date entered {0}. Date must be YYYY-MM-DD".format(args.since))

    engine = settings.DATABASES['default']['ENGINE']
    if engine == 'django.db.backends.sqlite3':
        sqlite_db_file = os.path.join(config['floodfront']['ProjectPath'], 'db.sqlite3')
        conn = sqlite.connect(sqlite_db_file)
        tty_print('Using SQLite engine.')
    elif engine == 'django.db.backdends.postgresql':
        conn = pg.connect(user="ryan", database="floodfront")
        tty_print('Using Postgres engine.')
    else:
        sys.stderr.write('Engine not supported: {0}'.format(engine))
        exit(1)
    cursor = conn.cursor()
    query = """ SELECT id, email, lat, lon, accuracy, created_on, marker_type, description
            FROM server_marker """
    
    if args.since is not None:
        tty_print("Searching for date {0}".format(args.since))
        query = query + "WHERE created_on >= '{0}'".format(args.since)
    else:
        now = strftime("%Y-%m-%d", gmtime())
        tty_print("Searching for date {0} (default today)".format(now))
        query = query + "WHERE created_on >= '{0}'".format(now)


    cursor.execute(query)
    result = cursor.fetchall()

    result = sorted(result, key=lambda row: row[5], reverse=True)

    filename = "marker.csv"
    if args.output is not None:
        filename = args.output

    if sys.stdout.isatty():
        with open(filename, 'w') as csvfile:
            writer = csv.writer(csvfile, dialect='excel')
            for row in result:
                if isinstance(row[5], datetime.datetime):
                    created_on = row[5].strftime("%Y-%m-%dT%H:%M:%S")
                elif isinstance(row[5], str):
                    created_on = str(datetime.datetime.strptime(row[5], '%Y-%m-%d %H:%M:%S.%f'))                    
                writer.writerow([row[0], row[1], round(float(row[2]), 6), round(float(row[3]), 6), round(float(row[4]), 6), created_on, type_to_class(row[6]), (str(row[7] or "No description."))])
    else:
        # Pipe mode
        writer = csv.writer(sys.stdout, dialect='excel')
        for row in result:
            if isinstance(row[5], datetime.datetime):
                created_on = row[5].strftime("%Y-%m-%dT%H:%M:%S")
            elif isinstance(row[5], str):
                created_on = str(datetime.datetime.strptime(row[5], '%Y-%m-%d %H:%M:%S.%f'))                    
            writer.writerow([row[0], row[1], round(float(row[2]), 6), round(float(row[3]), 6), round(float(row[4]), 6), created_on, type_to_class(row[6]), (str(row[7] or "No description."))])

def type_to_class(type):
    switch = {
        "WALKABLE" : "NotFlooded",
        "BORDER" : "FloodBoundary",
        "FLOOD" : "Flooded"
    }

    return switch.get(type, "Null")

main()