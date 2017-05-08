from lxml import etree
import pg8000 as pg
import argparse
import re

def main():
    """
    Main function
    """

    parser = argparse.ArgumentParser(description=""" Export FloodFront marker data into KML format. """)
    parser.add_argument('--after', type=str, help=""" Narrow selection to markers after this date. YYYY-MM-DD """)
    parser.add_argument('-o', '--output', type=str, help=""" File output name. """)

    args = parser.parse_args()
    if (re.search("^[0-9]{4}-[0-9]{2}-[0-9]{2}$", args.after) is None) and (args.after is not None):
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
#test
    for row in result:
        # print(row)
        if row[0] is None:
            # print("No ID found. Skipping.")
            continue
        placemark = etree.SubElement(document, "Placemark")
        point = etree.SubElement(placemark, "Point")
        coords = etree.SubElement(point, "coordinates")
        coords.text = "{0},{1}".format(round(float(row[2]), 6), round(float(row[3]), 6))
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
        timestamp_value.text = row[5].strftime("%Y-%m-%dT%H:%M:%S")
        marker_type = etree.SubElement(extended_data, "Data", name="markerType")
        marker_type_value = etree.SubElement(marker_type, "value")
        marker_type_value.text = type_to_class(row[6])
        description = etree.SubElement(extended_data, "Data", name="description")
        description_value = etree.SubElement(description, "value")
        description_value.text = str(row[7]) or "No description."
        
    file_name = "markers.kml"
    if args.output is not None:
        file_name = args.output + ".kml"

    out_file = open(file_name, 'w')
    out_file.write(etree.tostring(root, pretty_print=True, xml_declaration=True))
    out_file.close()

def type_to_class(type):
    switch = {
        "WALKABLE" : "NotFlooded",
        "BORDER" : "FloodBoundary",
        "FLOOD" : "Flooded"
    }

    return switch.get(type, "Null")

main()

