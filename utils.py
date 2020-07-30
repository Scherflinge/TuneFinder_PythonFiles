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
