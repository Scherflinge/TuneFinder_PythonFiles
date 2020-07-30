import argparse
from .ConvertWavToMidi import singleWavToMidi
from .ConvertMidiToFeatures import fileMidiToFeatures
from .tunefinderTestModel import testFileFromPaths
import os


def main(model_path, test_path):
    file_name = os.path.basename(test_path)
    test_folder = os.path.join(test_path+"_test")
    mid_path = os.path.join(test_folder, file_name+".mid")
    feature_path = os.path.join(test_folder, file_name+".json")
    if not os.path.exists(test_folder):
        print("making "+test_folder)
        os.makedirs(test_folder)
    singleWavToMidi(test_path, mid_path, skipExistingMidiFiles=False)
    fileMidiToFeatures(mid_path, feature_path, secondsPerClip=8,
                       featuresPerClip=200, spread=4, tempoSpread=3)
    return testFileFromPaths(model_path, feature_path)


if __name__ == "__main__":
    # main("model.m", "aint it fun.wav")
    parser = argparse.ArgumentParser()
    parser.add_argument("Model", type=str, help="path to model")
    parser.add_argument("File", type=str, help="path to audio file to test")
    args = vars(parser.parse_args())
    model_path = args["Model"]
    test_path = args["File"]
    main(model_path, test_path)
