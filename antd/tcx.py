# Copyright (c) 2012, Braiden Kindt.
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 
#   1. Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
# 
#   2. Redistributions in binary form must reproduce the above
#      copyright notice, this list of conditions and the following
#      disclaimer in the documentation and/or other materials
#      provided with the distribution.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDER AND CONTRIBUTORS
# ''AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY
# WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.


import logging
import time
import os
import glob
import shutil
import lxml.etree as etree
import lxml.builder as builder

import antd.plugin as plugin
import antd.garmin as garmin

_log = logging.getLogger("antd.tcx")

E = builder.ElementMaker(nsmap={
    None: "http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2",
    "ext": "http://www.garmin.com/xmlschemas/ActivityExtension/v2",
})

X = builder.ElementMaker(namespace="http://www.garmin.com/xmlschemas/ActivityExtension/v2")

class TcxPlugin(plugin.Plugin):
    
    tcx_output_dir = "."

    def data_availible(self, device_sn, format, files):
        if "raw" != format: return files
        processed = []
        result = []
        try:
            for file in files:
                _log.info("TcxPlugin: processing %s.", file)
                try:
                    dir = self.tcx_output_dir % {"device_id": hex(device_sn)}
                    if not os.path.exists(dir): os.makedirs(dir)
                    files = export_tcx(file, dir)
                    result.extend(files)
                    processed.append(file)
                except Exception:
                    _log.warning("Failed to process %s. Maybe a datatype is unimplemented?", file, exc_info=True)
            plugin.publish_data(device_sn, "tcx", result)
        finally:
            return processed


def format_time(gmtime):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", gmtime)

def format_intensity(intensity):
    if intensity == 1:
        return "Resting"
    else:
        return "Active"

def format_trigger_method(trigger_method):
    if trigger_method == 0: return "Manual"
    elif trigger_method == 1: return "Distance"
    elif trigger_method == 2: return "Location"
    elif trigger_method == 3: return "Time"
    elif trigger_method == 4: return "HeartRate"

def format_sport(sport):
    if sport == 0: return "Running"
    elif sport == 1: return "Biking"
    elif sport == 2: return "Other"

def format_sensor_state(sensor):
    if sensor: return "Present"
    else: return "Absent"

def create_wpt(wpt, sport_type):
    elements = [E.Time(format_time(wpt.time.gmtime))]
    if wpt.posn.valid:
        elements.extend([
            E.Position(
                E.LatitudeDegrees(str(wpt.posn.deglat)),
                E.LongitudeDegrees(str(wpt.posn.deglon)))])
    if wpt.alt is not None:
        elements.append(E.AltitudeMeters(str(wpt.alt)))
    if wpt.distance is not None:
        elements.append(E.DistanceMeters(str(wpt.distance)))
    if wpt.heart_rate:
        elements.append(E.HeartRateBpm(E.Value(str(wpt.heart_rate))))
    if wpt.cadence is not None and sport_type != 0:
        elements.append(E.Cadence(str(wpt.cadence)))
    #elements.append(E.SensorState(format_sensor_state(wpt.sensor)))
    if wpt.cadence is not None and sport_type == 0:
        elements.append(E.Extensions(X.TPX(X.RunCadence(str(wpt.cadence)))))
    #if len(elements) > 1:
    return E.Trackpoint(*elements)

def create_lap(lap, sport_type):
    elements = [
        E.TotalTimeSeconds("%0.2f" % (lap.total_time / 100.)),
        E.DistanceMeters(str(lap.total_dist)),
        E.MaximumSpeed(str(lap.max_speed)),
        E.Calories(str(lap.calories))]
    if lap.avg_heart_rate or lap.max_heart_rate:
        elements.extend([
            E.AverageHeartRateBpm(E.Value(str(lap.avg_heart_rate))),
            E.MaximumHeartRateBpm(E.Value(str(lap.max_heart_rate)))])
    elements.append(
        E.Intensity(format_intensity(lap.intensity)))
    if lap.avg_cadence is not None and sport_type != 0:
        elements.append(
            E.Cadence(str(lap.avg_cadence)))
    elements.append(E.TriggerMethod(format_trigger_method(lap.trigger_method)))
    wpts = [el for el in (create_wpt(w, sport_type) for w in lap.wpts) if el is not None]
    if wpts:
        elements.append(E.Track(*wpts))
    if lap.avg_cadence is not None and sport_type == 0:
        elements.append(E.Extensions(X.LX(X.AvgRunCadence(str(lap.avg_cadence)))))
    return E.Lap(
        {"StartTime": format_time(lap.start_time.gmtime)},
        *elements)

def create_activity(run):
    return E.Activity(
        {"Sport": format_sport(run.sport_type)},
        E.Id(format_time(run.time.gmtime)),
        *list(create_lap(l, run.sport_type) for l in run.laps))

def create_document(runs):
    doc = E.TrainingCenterDatabase(
        E.Activities(
            *list(create_activity(r) for r in runs)))
    return doc

def export_tcx(raw_file_name, output_dir):
    """
    Given a garmin raw packet dump, tcx to specified output directory.
    """
    with open(raw_file_name) as file:
        result = []
        host = garmin.MockHost(file.read())
        device = garmin.Device(host)
        run_pkts = device.get_runs()
        runs = garmin.extract_runs(device, run_pkts)
        for run in runs:
            tcx_name = time.strftime("%Y%m%d-%H%M%S.tcx", run.time.gmtime)
            tcx_full_path = os.path.sep.join([output_dir, tcx_name])
            _log.info("tcx: writing %s -> %s.", os.path.basename(raw_file_name), tcx_full_path)
            with open(tcx_full_path, "w") as file:
                doc = create_document([run])
                file.write(etree.tostring(doc, pretty_print=True, xml_declaration=True, encoding="UTF-8"))
            result.append(tcx_full_path)
        return result


# vim: ts=4 sts=4 et
