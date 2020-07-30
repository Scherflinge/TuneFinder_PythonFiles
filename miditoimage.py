from PIL import Image, ImageDraw
import ConvertMidiToFeatures
import math
from scipy.stats import zscore
from utils import (midiNoteToFrequency, frequencyToMidiNote, MidiEvent)

OFF = 0
VALID = 1
DELETE = 2
FUNDAMENTAL = 3
ADD = 4

CONFLICT = 5
CONFLICT_ADD = 6

green_pixel = (0, 255, 0)
red_pixel = (255, 0, 0)
blue_pixel = (0, 0, 255)
black_pixel = (0, 0, 0)
white_pixel = (255, 255, 255)
yellow_pixel = (255, 255, 0)
dark_red_pixel = (144, 0, 0)

ORIGINAL_NOTES = 0
COMPARISON = 1
AFTER = 2

PIXEL_COLORING = {
    (OFF, ORIGINAL_NOTES): black_pixel,
    (OFF, COMPARISON): black_pixel,
    (OFF, AFTER): black_pixel,

    (VALID, ORIGINAL_NOTES): white_pixel,
    (VALID, COMPARISON): white_pixel,
    (VALID, AFTER): white_pixel,

    (FUNDAMENTAL, ORIGINAL_NOTES): white_pixel,
    (FUNDAMENTAL, COMPARISON): green_pixel,
    (FUNDAMENTAL, AFTER): white_pixel,

    (ADD, ORIGINAL_NOTES): black_pixel,
    (ADD, COMPARISON): blue_pixel,
    (ADD, AFTER): white_pixel,

    (DELETE, ORIGINAL_NOTES): white_pixel,
    (DELETE, COMPARISON): red_pixel,
    (DELETE, AFTER): black_pixel,

    (CONFLICT, ORIGINAL_NOTES): white_pixel,
    (CONFLICT, COMPARISON): yellow_pixel,
    (CONFLICT, AFTER): white_pixel,

    (CONFLICT_ADD, ORIGINAL_NOTES): black_pixel,
    (CONFLICT_ADD, COMPARISON): dark_red_pixel,
    (CONFLICT_ADD, AFTER): white_pixel
}


def main():
    try:
        cleanMidi("TuneFinder\\MidtermMidi\\All Star.mid")
    except:
        cleanMidi("MidtermMidi\\All Star.mid")


def cleanMidi(filepath, features_per_second=40):
    events = ConvertMidiToFeatures.convertMidiToEvents(filepath)

    midiend = events[-1].time_off

    width = int(features_per_second*midiend)
    # 127 possible midi notes
    height = 127

    # remove notes if they are too short
    # NOTE This ended up working bad for quick rhythms
    # events = [x for x in events if x[3]-x[2] > 0.1]

    # turn events into dictionaries
    eventgrid = midi_events_to_dicts(events, features_per_second)

    # get rid of found harmonics
    removeHarmonics(eventgrid)

    # get rid of notes outside of standard deviation
    # deleteOutliers(eventgrid)

    # this is for extrapolating values to neighbors
    extrapolateNeighbors(eventgrid)
    # print_grids(eventgrid)
    remove_lower_conflicts(eventgrid)
    # print_grids(eventgrid)
    final_events = dicts_to_midi_events(eventgrid, features_per_second)
    # print(final_events)
    return final_events


def remove_lower_conflicts(eventgrid):
    for audio_slice in eventgrid:
        if len(audio_slice) == 0:
            continue
        if len(audio_slice) > 1:

            notes = list(audio_slice)
            notes.sort()

            min_note = None

            for x in notes:
                if audio_slice[x] not in (OFF, DELETE):
                    min_note = x
                    break

            if not min_note:
                break

            for x in list(audio_slice):
                if x is not min_note:
                    audio_slice.pop(x)


def print_grids(eventgrid):
    height = 127
    width = len(eventgrid)
    for iters in range(3):
        img = Image.new('RGB', (width, height))

        for x in range(width):
            vert = eventgrid[x]
            for y in range(height):
                cur_pixel = vert[y] if y in vert else OFF

                if (cur_pixel, iters) in PIXEL_COLORING:
                    value = PIXEL_COLORING[(cur_pixel, iters)]
                else:
                    value = (0, 0, 0)

                img.putpixel((x, height - y-1), value)
        img.show()
        img.save("midiTest_zscore_{}.png".format(iters))


def dicts_to_midi_events(dicts, features_per_second):
    to_return = []
    holdover = {}
    for i, this_dict in enumerate(dicts):
        this_time = i/features_per_second

        notes_to_remove = []

        for note_from_last_time in holdover:
            # check if any notes that we had last moment have now ended
            if note_from_last_time not in this_dict:
                notes_to_remove.append(note_from_last_time)

        for rem in notes_to_remove:
            starttime = holdover.pop(rem)
            to_return.append(MidiEvent(rem, 60, starttime, this_time))

        for this_key in this_dict:
            # Don't look at notes that we are removing
            if this_dict[this_key] in (OFF, DELETE):
                continue

            # add a note if it just started playing been added yet
            if this_key not in holdover:
                holdover[this_key] = this_time

    i += 1
    this_time = i/features_per_second

    for last_notes in list(holdover):
        starttime = holdover.pop(last_notes)
        to_return.append(MidiEvent(last_notes, 60, starttime, this_time))
    return to_return


def midi_events_to_dicts(events, features_per_second):
    midiend = events[-1].time_off
    width = int(features_per_second*midiend)
    eventgrid = [{} for x in range(width)]
    for event in events:
        beginbucket = int((event.time_on / midiend)*width)
        endbucket = int((event.time_off / midiend)*width)
        for n in range(beginbucket, endbucket):
            eventgrid[n][event.note] = VALID
    return eventgrid


def removeHarmonics(eventgrid):
    for vert in eventgrid:
        notes = [note for note in vert]
        frequencies = [freq for freq in map(midiNoteToFrequency, notes)]
        frequencies.sort()
        fundamentalFrequency = find_harmonic_fundamental(frequencies)
        fundamentalMidi = None if fundamentalFrequency == None else frequencyToMidiNote(
            fundamentalFrequency)
        # print("{} {}".format(fundamentalMidi, notes))
        if fundamentalMidi:
            for n in notes:
                if n == fundamentalMidi:
                    vert[n] = FUNDAMENTAL
                else:
                    vert[n] = DELETE
            if fundamentalMidi not in notes:
                vert[fundamentalMidi] = ADD
        else:
            for n in notes:
                vert[n] = VALID
        # found_fundamentals.append(vert)


def deleteOutliers(eventgrid, outlierScore=1):
    current_notes = []
    for verts in eventgrid:
        current_notes.extend([x for i, x in enumerate(verts)])

    deviations = list(zscore(current_notes))
    deviated_numbers = [current_notes[i]
                        for i, x in enumerate(deviations) if x > outlierScore]
    deviated_numbers = list(set(deviated_numbers))
    for vert in eventgrid:
        for num in deviated_numbers:
            if num in vert:
                # pass
                vert[num] = DELETE


def extrapolateNeighbors(eventgrid):
    width = len(eventgrid)
    for i, vert in enumerate(eventgrid):
        for note in vert:
            if note in (VALID, OFF, ADD):
                continue
            begin_index = i
            end_index = i
            while(begin_index - 1 >= 0 and note in eventgrid[begin_index-1]):
                begin_index -= 1

            while(end_index + 1 < width and note in eventgrid[end_index+1]):
                end_index += 1

            these_notes = list(set([eventgrid[n][note]
                                    for n in range(begin_index, end_index+1)]))

            val = None

            assert(len(these_notes) > 0)
            if len(these_notes) == 1:
                val = vert[note]
            elif len(these_notes) > 1:
                if DELETE in these_notes and VALID in these_notes:
                    val = DELETE
                elif DELETE in these_notes and ADD in these_notes:
                    val = CONFLICT_ADD
                elif DELETE in these_notes and FUNDAMENTAL in these_notes:
                    val = CONFLICT
                elif VALID in these_notes and FUNDAMENTAL in these_notes:
                    val = FUNDAMENTAL
                elif VALID in these_notes and ADD in these_notes:
                    val = ADD

            for v in range(begin_index, end_index+1):
                if val == None:
                    eventgrid[v][note] = eventgrid[v][note]
                else:
                    eventgrid[v][note] = val


def find_harmonic_fundamental(frequencies: list, tolerance=0.05, add_new_fundamental=False):
    if 0 <= len(frequencies) <= 1:
        return None
    frequencies = frequencies.copy()
    frequencies.sort()
    diffs = []
    for i in range(len(frequencies)-1):
        diffs.append(frequencies[i+1]-frequencies[i])
    iter_range = 2 if add_new_fundamental else 1
    best_found = None
    for iters in range(iter_range):
        if iters == 1:
            frequencies.append(frequencies[0]/2)
            frequencies.sort()

        for i, root in enumerate(frequencies):
            ratios = []
            for j, harmonic in enumerate(frequencies):
                # if
                this_ratio = (harmonic/root)
                distance_to_harmonic = this_ratio % 1
                harmonic_ranking = int(this_ratio+0.5)-1
                if distance_to_harmonic > 0.5:
                    distance_to_harmonic = 1-distance_to_harmonic
                harmonic_purity = 1-(distance_to_harmonic*2)
                ratios.append(
                    (distance_to_harmonic, harmonic_ranking, harmonic_purity))
            found_harmonics = [frequencies[i] for i, x in enumerate(ratios) if (
                x[0] < tolerance and x[1] > 0)]
            allscore = [(1/x[1])*x[2] for x in ratios if x[1] > 0]
            score = sum(allscore)

            # if len(found_harmonics) > 1/3*len(ratios):
            if not best_found:
                best_found = (root, score)
            else:
                if score > best_found[1]:
                    best_found = (root, score)
    return best_found[0] if best_found else None


if __name__ == "__main__":
    main()
