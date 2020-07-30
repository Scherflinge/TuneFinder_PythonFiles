import mido
import heapq
import math


class MidiEvent:
    def __init__(self, Note: int, Velocity: int, Time_On: float, Time_Off: float):
        self.note = Note
        self.velocity = Velocity
        self.time_on = Time_On
        self.time_off = Time_Off

    def length(self):
        return self.time_off-self.time_on

    def __str__(self):
        return "{} lasts {} from {} to {}".format(length(self.note, self.length(), self.time_on, self.time_off))


def frequencyToMidiNote(frequency):
    return round((12*math.log(frequency/440))/math.log(2)+69)


def midiNoteToFrequency(note):
    return 440 * (2**(1./12))**(note-69)


def midiNoteToName(note):
    note -= 12
    oct = note//12
    rem = note % 12
    notes = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    a = notes[rem]+str(oct)
    return a


def convertMidiToEvents(midifile):
    '''
    returns Midi events from the file
    '''
    mid = mido.MidiFile(midifile)
    events = []
    for track in mid.tracks:
        tick = 0
        currentTime = 0
        holdoverNotes = {}
        for msg in track:
            if msg.__class__.__name__ is not "MetaMessage":
                # Update the summed time
                tick += msg.time
                currentTime = mido.tick2second(
                    tick, mid.ticks_per_beat, 500000)

                if msg.type == 'note_on':
                    holdoverNotes[msg.note] = MidiEvent(
                        msg.note, msg.velocity, currentTime, 0)
                elif msg.type == 'note_off':
                    # TODO maybe it should check if we're in a new feature first?
                    #
                    # Once a note is released, add it to to the current feature
                    info = holdoverNotes.pop(msg.note)
                    info.time_off = currentTime
                    events.append(info)
        if len(holdoverNotes.keys()) > 0:
            raise Exception("Notes didn't end")
    return events


def convertEventsToMidi(events: list):
    '''
    takes in a list of MidiEvents and returns a Midi object
    '''
    midievents = []
    for event in events:
        heapq.heappush(midievents, (event.time_on, "on",
                                    event.note, event.velocity))
        heapq.heappush(midievents, (event.time_off, "off",
                                    event.note, event.velocity))
    midievents = [heapq.heappop(midievents) for x in range(len(midievents))]

    mid = mido.MidiFile()
    t = mid.add_track(name="Test Track")
    lastTick = 0
    for ev in midievents:
        tick = mido.second2tick(ev[0], mid.ticks_per_beat, 500000)
        tickDif = tick - lastTick
        lastTick = tick
        mType = "note_on" if ev[1] == "on" else "note_off"
        tickDif += 0.5
        tickDif = math.floor(tickDif)
        message = mido.Message(mType, note=ev[2], time=tickDif)
        t.append(message)

    t.append(mido.MetaMessage("end_of_track"))
    return mid
