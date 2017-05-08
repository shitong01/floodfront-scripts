#!/usr/bin/env python
from os import environ as env
import csv
import pg8000 as pg
import re
import argparse

def main():
    parser = argparse.ArgumentParser(description=""" Export FloodFront marker data into CSV format. """)
    parser.add_argument('--after', type=str, help=""" Narrow selection to markers after this date. YYYY-MM-DD """)
    parser.add_argument('-o', '--output', type=str, help=""" File output name. """)

    args = parser.parse_args()
    if (args.after is not None) and (re.search("^[0-9]{4}-[0-9]{2}-[0-9]{2}$", args.after) is None):
        raise ValueError("Invalid date entered {0}. Date must be YYYY-MM-DD".format(args.after))

    conn = pg.connect(user="ryan", database="floodfront")
    cursor = conn.cursor()
    query = """ SELECT marker.id, email, lat, lon, error_margin, created, marker_type, description
            FROM marker 
            FULL OUTER JOIN app_user 
            ON marker.user_id=app_user.id """
    
    if args.after is not None:
        print "Searching for date {0}".format(args.after)
        query = query + "WHERE created >= '{0}'".format(args.after)

    cursor.execute(query)
    result = cursor.fetchall()

    result = sorted(result, key=lambda row: row[5], reverse=True)

    filename = "marker.csv"
    if args.output is not None:
        filename = args.output + ".csv"

    with open(filename, 'w') as csvfile:
        writer = csv.writer(csvfile, dialect='excel')
        for row in result:
            if row[0] and row[1] and row[2] and row[3] and row[4] and row[5] and row[6]:
                writer.writerow([row[0], row[1], round(float(row[2]), 6), round(float(row[3]), 6), round(float(row[4]), 6), row[5].strftime("%Y-%m-%dT%H:%M:%S"), type_to_class(row[6]), (str(row[7] or "No description."))])

def type_to_class(type):
    switch = {
        "WALKABLE" : "NotFlooded",
        "BORDER" : "FloodBoundary",
        "FLOOD" : "Flooded"
    }

    return switch.get(type, "Null")

main()