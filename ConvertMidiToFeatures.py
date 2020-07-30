import time
from sklearn import preprocessing
import numpy as np
import math
import os
import json
from .FileManagement import listAllFiles
import shutil
from itertools import product
import progressbar
from .utils import (MidiEvent, convertMidiToEvents, convertEventsToMidi)
from .miditoimage import cleanMidi


def timetoindex(time, cliplength, featurecount, offset):
    '''
    Given a time, the length of a clip, what the count of features are per clip 
    and the offset of how long was blank at the beginning of the audio, it will 
    tell you what the exact index the feature belongs to. 
    '''
    t = time+offset
    clip = 0
    clip = t // cliplength
    if offset < 0:
        clip += abs(offset // cliplength)

    feature = (t % cliplength) // (cliplength/featurecount)
    return int(feature + clip*featurecount)


def midiToFeatures(events, offset=0, secondsPerClip=20, featuresPerClip=40):
    '''
    Given a list of MidiEvents, the length of a clip, what the count of features are per clip 
    and the offset of how long was blank at the beginning of the audio, it will return a list of lists of normalized values.
    '''
    # mid = mido.MidiFile(fileName)

    # fullTime = mid.length
    numFeatures = featuresPerClip

    secondsPerFeature = secondsPerClip/featuresPerClip
    features = []
    for this_midi_event in events:
        start = timetoindex(this_midi_event.time_on,
                            secondsPerClip, featuresPerClip, offset)
        end = timetoindex(this_midi_event.time_off,
                          secondsPerClip, featuresPerClip, offset)
        while len(features) < end:
            features.append([])
        for i in range(start, end, 1):
            features[i].append(
                (this_midi_event.note, this_midi_event.velocity))
    while(len(features) % featuresPerClip != 0):
        # add empty lists to pad out the features to a number divisible by the feature count
        features.append([])
    # lengths = list(map(len, features))
    avgfeatures = list(map(notesAverage, features))
    clips = []
    for i in range(int(len(avgfeatures)//featuresPerClip)):
        normalized = normalizeData(
            avgfeatures[int(i*numFeatures):int((i+1)*numFeatures)])
        if normalized != None:
            clips.append(normalized)

    return clips


def notesAverage(notes):
    # If no notes are given, respond "NA"
    if notes == [] or notes == {}:
        return np.nan
    # Description:
    # Average notes using velocity
    noteVals = None
    weights = None
    if isinstance(notes, dict):
        noteVals = [notes[x][0] for x in notes.keys()]
        weights = [notes[x][1] for x in notes.keys()]
    else:
        noteVals = [x[0] for x in notes]
        weights = [x[1] for x in notes]
    for g in range(len(noteVals)):
        noteVals[g] = noteVals[g] * weights[g] / sum(weights)
    return round(sum(noteVals), 3)


def normalizeData(data, high=20, low=10, off=0):
    '''
    takes numbers and normalizess them between a high and low, also option for what the value to be if the value is off.
    '''

    num = []
    nas = []

    for i in range(len(data)):
        if math.isnan(data[i]):
            nas.append((i, off))
        else:
            num.append(data[i])

    if len(num) < (1/3 * len(data)):
        return None

    mi = min(num)
    num2 = [x-mi for x in num]
    ma = max(num2)
    if ma == 0:
        num2 = [(high+low)/2 for x in num]
    else:
        num2 = [round((x/ma)*(high-low)+low, 3) for x in num2]
    for x in nas:
        num2.insert(x[0], x[1])
    return num2


def fileMidiToFeatures(inputFile, outputFile, offset=0, secondsPerClip=20, featuresPerClip=40, skipExistingFiles=False, spread=0, tempoSpread=0):
    if not os.path.exists(inputFile):
        return

    if not os.path.exists(os.path.dirname(outputFile)):
        if os.path.dirname(outputFile) is not "":
            os.makedirs(os.path.dirname(outputFile))
    elif os.path.exists(outputFile):
        if skipExistingFiles:
            return

    print("Converting {} to features, {}...".format(inputFile, outputFile))
    result = []
    spRange = [0]
    if spread != 0:
        # spRange = range(-spread, spread)
        spRange = np.linspace(-spread, 0, spread*2+1).tolist()
    tmpRange = [0]
    if tempoSpread != 0:
        tmpRange = np.linspace(
            secondsPerClip-tempoSpread, secondsPerClip+tempoSpread, (tempoSpread*2)*2+1).tolist()

    combos = [x for x in product(spRange, tmpRange)]
    counter = 0
    events = convertMidiToEvents(inputFile)
    # print(len(events))
    events = cleanMidi(inputFile)
    # print(len(events))
    for i, j in progressbar.progressbar(combos):
        result.extend(midiToFeatures(events, offset=offset+i,
                                     secondsPerClip=secondsPerClip+j, featuresPerClip=featuresPerClip))

    writeData(outputFile, result)

    print("Finished conversion.\n")


def writeData(path, data):
    with open(path, "w") as f:
        f.write(json.dumps(data))


def folderMidiToFeatures(inputFolder, outputFolder, offset=0, secondsPerClip=20, featuresPerClip=40, skipExistingFiles=False, spread=0, tempoSpread=0):
    print("Converting folder {} to features, {}...".format(
        inputFolder, outputFolder))
    for x in FileManagement.listAllFiles(inputFolder, relative=True):
        fileMidiToFeatures(os.path.join(inputFolder, x),
                           os.path.join(outputFolder, os.path.splitext(x)[0]+".json"), offset=offset, secondsPerClip=secondsPerClip, featuresPerClip=featuresPerClip, skipExistingFiles=skipExistingFiles, spread=spread, tempoSpread=tempoSpread)
    print("Finished Folder Conversion.")


if __name__ == "__main__":
    # a = convertMidiToEvents("new Midi Test.mid")
    fileMidiToFeatures("MidtermMidi/All Star.mid", "new Midi Test.json")
    # fileMidiToFeatures("test.mid", "testfeature.json",
    #    secondsPerClip=8, featuresPerClip=200)
