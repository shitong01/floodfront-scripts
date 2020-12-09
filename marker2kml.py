#!/usr/bin/env python
from lxml import etree
from time import gmtime, strftime
from datetime import datetime
import pg8000 as pg
import argparse
import re
import configparser as conf
import sqlite3 as sqlite
import os
import sys
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

    parser = argparse.ArgumentParser(description=""" Export FloodFront marker data into KML format. """)
    parser.add_argument('--since', type=str, help=""" Narrow selection to markers after this date. YYYY-MM-DD """)
    parser.add_argument('-o', '--output', type=str, help=""" File output name. """)

    args = parser.parse_args()
    if (args.since is not None) and (re.search("^[0-9]{4}-[0-9]{2}-[0-9]{2}$", args.since) is None):
        raise ValueError("Invalid date entered {0}. Date must be YYYY-MM-DD".format(args.since))

    engine = settings.DATABASES['default']['ENGINE']
    if engine == 'django.db.backends.sqlite3':
        sqlite_db_file = os.path.join(config['floodfront']['ProjectPath'], 'db.sqlite3')
        conn = sqlite.connect(sqlite_db_file)
    elif engine == 'django.db.backdends.postgresql':
        conn = pg.connect(user=db_username, database=db_connection_name)
    else:
        sys.stderr.write('Database engine {0} not supported'.format(engine))
        exit(1)
    tty_print('Using {0} engine.'.format(engine))

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

    #0 markerId
    #1 email
    #2 lat
    #3 lon
    #4 error
    #5 timestamp
    #6 markerClass
    #7 description


    root = etree.Element("kml", xmlns="http://www.opengis.net/kml/2.2")
    document = etree.SubElement(root, "Folder")
    name = etree.SubElement(document, "name")
    name.text = "markers"

    result = sorted(result, key=lambda row: row[5], reverse=True)

    for row in result:
        # print(row)
        if row[0] is None:
            # print("No ID found. Skipping.")
            continue
        placemark = etree.SubElement(document, "Placemark")
        point = etree.SubElement(placemark, "Point")
        coords = etree.SubElement(point, "coordinates")
        coords.text = "{0},{1}".format(round(float(row[3]), 6), round(float(row[2]), 6))
        # heading = etree.SubElement(placemark, "heading")
        # heading.text = str(row[3])
        extended_data = etree.SubElement(placemark, "ExtendedData")
        marker_id = etree.SubElement(extended_data, "Data", name="id")
        marker_id_value = etree.SubElement(marker_id, "value")
        marker_id_value.text = str(row[0])
        user_id = etree.SubElement(extended_data, "Data", name="userId")
        user_id_value = etree.SubElement(user_id, "value")
        user_id_value.text = str(row[1])
        error_margin = etree.SubElement(extended_data, "Data", name="uncertainty")
        error_margin_value = etree.SubElement(error_margin, "value")
        if row[4] is not None:
            error_margin_value.text = str(round(float(row[4]), 6))
        else:
            error_margin_value.text = "-1"
        timestamp = etree.SubElement(extended_data, "Data", name="obsTime")
        timestamp_value = etree.SubElement(timestamp, "value")
        if engine == 'django.db.backends.sqlite3':
            # Date type in sqlite are strings
            timestamp_value.text = str(datetime.strptime(row[5], '%Y-%m-%d %H:%M:%S.%f'))
        elif engine == 'django.db.backdends.postgresql':
            timestamp_value.text = row[5].strftime("%Y-%m-%dT%H:%M:%S")
        else:
            sys.stdout.write("Unsupported engine: {0}".format(engine))
            exit(1)
        marker_type = etree.SubElement(extended_data, "Data", name="markerType")
        marker_type_value = etree.SubElement(marker_type, "value")
        marker_type_value.text = type_to_class(row[6])
        description = etree.SubElement(extended_data, "Data", name="description")
        description_value = etree.SubElement(description, "value")
        description_value.text = str(row[7] or "No description.")
        

    if sys.stdout.isatty():
        file_name = "markers.kml"
        if args.output is not None:
            file_name = args.output + ".kml"
        else:
            print('Using default name `markers.kml` for output file.')
        # In Python 3, must specify "write binary" -- wb mode
        out_file = open(file_name, 'wb')
        out_file.write(etree.tostring(root, pretty_print=True, xml_declaration=True))
        out_file.close()
    else:
        sys.stdout.buffer.write(etree.tostring(root, pretty_print=True, xml_declaration=True))

def type_to_class(type):
    switch = {
        "WALKABLE" : "NotFlooded",
        "BORDER" : "FloodBoundary",
        "FLOOD" : "Flooded"
    }

    return switch.get(type, "Null")

main()

