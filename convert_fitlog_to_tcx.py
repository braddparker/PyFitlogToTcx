##############################################################################
# MIT License
#
# Copyright (c) 2024 Brad D. Parker
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
##############################################################################

##############################################################################
# This program will convert a SportTracks FITLOG file into individual Garmin
# TCX files, one per activity. 
#
# Author: Brad D. Parker
# Contact: bdparker@gmail.com
##############################################################################

import os
import argparse
from datetime import datetime, timedelta
from lxml import etree as ET
from lxml import objectify

def convert_fitlog_to_tcx(fitlog_filename, output_folder):

    fitlog_tree = ET.parse(fitlog_filename)
    fitlog_root = fitlog_tree.getroot()

    print(f"Starting")

    for activity in fitlog_root.findall(".//Activity", fitlog_root.nsmap):
        metadata = activity.find("Metadata", fitlog_root.nsmap)
        duration = activity.find("Duration", fitlog_root.nsmap)
        distance = activity.find("Distance", fitlog_root.nsmap)
        calories = activity.find("Calories", fitlog_root.nsmap)
        category = activity.find("Category", fitlog_root.nsmap)
        location = activity.find("Location", fitlog_root.nsmap)
        start_time_str = activity.get("StartTime")
        start_time = datetime.strptime(start_time_str, "%Y-%m-%dT%H:%M:%SZ")

        print(f"Converting activity starting at {start_time}...")
        xsi_type = ET.QName("http://www.w3.org/2001/XMLSchema-instance", "type")
        schemaLocation_type = ET.QName("http://www.w3.org/2001/XMLSchema-instance", "schemaLocation")
        tcx_nslist = {
        'ns5':'http://www.garmin.com/xmlschemas/ActivityGoals/v1',
        'ns3':'http://www.garmin.com/xmlschemas/ActivityExtension/v2',
        'ns2':'http://www.garmin.com/xmlschemas/UserProfile/v2', 
        'ns4':'http://www.garmin.com/xmlschemas/ProfileExtension/v1', 
        'xsi':'http://www.w3.org/2001/XMLSchema-instance', 
        None: 'http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2'}

        tcx_root = ET.Element("TrainingCenterDatabase", 
                              {schemaLocation_type: "http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2 http://www.garmin.com/xmlschemas/TrainingCenterDatabasev2.xsd"}, 
                              nsmap=tcx_nslist)
        tcx_activities = ET.SubElement(tcx_root, "Activities")
        sport_name=category.get("Name")
        if sport_name == "My Activities":
            sport_name = "Running"

        tcx_activity = ET.SubElement(tcx_activities, "Activity", Sport=sport_name)
        tcx_id = ET.SubElement(tcx_activity, "Id").text=activity.get("Id")
        if metadata is not None:
            creator = ET.SubElement(tcx_activity, "Creator", {xsi_type: "Device_t"})
            name = ET.SubElement(creator, "Name")
            name.text = metadata.get("Source")

        if duration is not None:
           ET.SubElement(tcx_activity, "TotalTimeSeconds").text=duration.get("TotalSeconds")
        if distance is not None:
           ET.SubElement(tcx_activity, "DistanceMeters").text=distance.get("TotalMeters")
        if calories is not None:
            ET.SubElement(tcx_activity, "Calories").text=calories.get("TotalCal")
        if activity.find("Laps", fitlog_root.nsmap) is not None:
            laps=activity.find("Laps", fitlog_root.nsmap).findall("Lap", fitlog_root.nsmap)
            number_of_laps=len(laps)
            lap_number=0
            for lap in laps:
                lap_start_time_str = lap.get("StartTime")
                lap_start_time = datetime.strptime(lap_start_time_str, "%Y-%m-%dT%H:%M:%SZ")
                lap_duration = lap.get("DurationSeconds")
                lap_caloriesElem = lap.find("Calories", fitlog_root.nsmap)
                next_lap_start_time = 0
                if lap_number+1 < number_of_laps:
                    next_lap_start_str = laps[lap_number+1].get("StartTime")
                    next_lap_start_time = datetime.strptime(next_lap_start_str, "%Y-%m-%dT%H:%M:%SZ")

                tcx_lap = ET.SubElement(tcx_activity, "Lap", StartTime=lap_start_time.strftime("%Y-%m-%dT%H:%M:%SZ"))
                ET.SubElement(tcx_lap, "TotalTimeSeconds").text=lap_duration

                if lap_caloriesElem is not None:
                    ET.SubElement(tcx_lap, "Calories").text=lap_caloriesElem.get("TotalCal")
                tcx_track = ET.SubElement(tcx_lap, "Track")
                for point in activity.findall(".//pt", fitlog_root.nsmap):
                    timeoffset = int(point.get("tm"))
                    point_time=(start_time + timedelta(seconds=timeoffset))
                    if (point_time >= lap_start_time) and ((next_lap_start_time == 0) or (point_time < next_lap_start_time)):
                        trackpoint = ET.SubElement(tcx_track, "Trackpoint")
                        ET.SubElement(trackpoint, "Time").text = point_time.strftime("%Y-%m-%dT%H:%M:%SZ")
                        tk_position = ET.SubElement(trackpoint, "Position")#.extend([ET.Element("LatitudeDegrees"), ET.Element("LongitudeDegrees")])
                        ET.SubElement(tk_position, "LatitudeDegrees").text = point.get("lat")
                        ET.SubElement(tk_position, "LongitudeDegrees").text = point.get("lon")
                        ET.SubElement(trackpoint, "AltitudeMeters").text = point.get("ele")
                lap_number = lap_number + 1

        tcx_tree = ET.ElementTree(tcx_root)
        tcx_filename = f"{output_folder}/{start_time.strftime('%Y%m%dT%H%M%SZ')}.tcx"
        if not os.path.exists(output_folder):
            # If directory doesn't exist, create it
            os.makedirs(output_folder)
        tcx_tree.write(tcx_filename, xml_declaration=True, encoding='UTF-8', pretty_print=True)
        print(f"Activity converted. TCX file saved at {tcx_filename}")

if __name__ == "__main__":
    # Create argument parser
    parser = argparse.ArgumentParser(description='Converts a SportTracks fitlog file into Garmin TCX files')

    # Add arguments
    parser.add_argument('--input', type=str, default='B:/sporttracks/allactivities.fitlog', help='Input fitlog file')
    parser.add_argument('--output', type=str, default='B:/sporttracks/output_folder', help='Output directory')

    # Parse the arguments
    args = parser.parse_args()

    # Print the names in the desired order
    print(f"Reading FITLOG from {args.input} and saving as TCX at {args.output}")
    fitlog_filename = args.input
    output_folder = args.output
    convert_fitlog_to_tcx(fitlog_filename, output_folder)