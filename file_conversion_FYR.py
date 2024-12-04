import os
import pydicom
import pandas as pd
import gzip
import shutil
import json
import csv
from rt_utils import RTStructBuilder
import numpy as np
import SimpleITK as sitk
from helper import winapi_path, bqml_to_suv

IMAGE_FOLDER_PATH = "./data"
ATTRIBUTE_FILE_NAME = "attributes.csv"
HEADERS_FILE_NAME = "headers.json"
QUERY_FILE_PATH = os.getenv('IMAGEDRIVE_CSV')
# DELETE_UNMATCHED_SERIES = os.getenv('DELETE_UNMATCHED_SERIES')
RESTRUCTURE_FOLDERS = True

SAVE_JSON = False


def getDicomHeaders(file):
    # returns the headers of a dicom file as a python dictionary, excluding the actual image data.
    dicomHeaders = file.to_json_dict()
    try:
        dicomHeaders.pop('7FE00010')
    except:
        pass
    return dicomHeaders


def dicomToNifti(file, seriesDir, savePath):
    # converts DICOM series in the seriesDir to NIFTI image in the savePath specified
    patientID, modality, studyDate = getattr(file, 'PatientID', None), getattr(file, 'Modality', None), getattr(file, 'StudyDate', None)
    reader = sitk.ImageSeriesReader()
    seriesNames = reader.GetGDCMSeriesFileNames(seriesDir)
    reader.SetFileNames(seriesNames)
    image = reader.Execute()

    if modality == 'PT':
        pet = pydicom.dcmread(seriesNames[0])  # read one of the images for header info
        suv_factor = bqml_to_suv(pet)
        image = sitk.Multiply(image, suv_factor)

    sitk.WriteImage(image, os.path.join(
        savePath, f'{patientID}_{modality}_{studyDate}.nii.gz'), imageIO='NiftiImageIO')


def sortParallelLists(list1, list2):
    # given two equal length, parallel lists, sort the first list and re-arrange the second list accordingly
    if len(list1) > 0 and len(list2) >0:
        tuples = zip(*sorted(zip(list1, list2)))
        list1, list2 = [list(tuple) for tuple in tuples]
    return list1, list2



def getNewFilePath(file, filePath, format):
    # generate the mask file paths based on DICOM attributes of the current label and its file path
    fileName = os.path.splitext(os.path.basename(filePath))[0]
    fileExtension = os.path.splitext(os.path.basename(filePath))[1]
    patientID, modality, studyDate = getattr(file, 'PatientID', None), getattr(file, 'Modality', None), getattr(file, 'StudyDate', None)
    newFilePath = filePath.replace("DICOM", "NIFTI").replace(fileName, f'{patientID}_{modality}_{studyDate}').replace(fileExtension, '.' + format)
    return newFilePath


def absoluteFilePaths(directory):
    # return the absolute file paths of all files inside a given directory
    paths = []
    for dirpath, _, filenames in os.walk(directory):
        for f in filenames:
            paths.append(os.path.abspath(os.path.join(dirpath, f)))
    return paths


def buildMaskArray(file, seriesPath, labelPath) -> np.ndarray:
    rtstruct = RTStructBuilder.create_from(
        dicom_series_path=seriesPath, rt_struct_path=labelPath)
    
    rois = rtstruct.get_roi_names()
    masks = []
    for roi in rois:
        mask_3d = rtstruct.get_roi_mask_by_name(roi).astype(int)
        masks.append(mask_3d)

    final_mask = sum(masks)  # sums element-wise
    final_mask = np.where(final_mask>=1, 1, 0)
    # Reorient the mask to line up with the reference image
    final_mask = np.moveaxis(final_mask, [0, 1, 2], [1, 2, 0])

    return final_mask

def buildMasks(file, seriesPath, labelPath):
    final_mask = buildMaskArray(file, seriesPath, labelPath)

    # Load original DICOM image for reference
    reader = sitk.ImageSeriesReader()
    dicom_names = reader.GetGDCMSeriesFileNames(seriesPath)
    reader.SetFileNames(dicom_names)
    ref_img = reader.Execute()

    # Properly reference and convert the mask to an image object
    mask_img = sitk.GetImageFromArray(final_mask)
    mask_img.CopyInformation(ref_img)
    sitk.WriteImage(mask_img, getNewFilePath(file, labelPath, 'nii.gz'), imageIO="NiftiImageIO")


def convertFiles():
    # parallel lists of file paths, directoreies, and attributes of DICOM files in the same directory
    dicomFilePaths = []
    dicomFileDirs = []
    dicomFileTraits = []
    dicomFileHeaders = []
    dicomFileHeaderKeys = []

    # list of all labels and series instance UIDs
    labelInstanceUIDs = []
    seriesInstanceUIDs = []

    # lists of RTSTRUCT file paths and their corresponding DICOM series
    labelPaths = []
    seriesPaths = []

    for x in range(3):
        for root, dirs, files in os.walk(IMAGE_FOLDER_PATH):
            dirname = None
            for dir in dirs:
                if len(dir) > 20:
                    i = 5
                    while os.path.exists(os.path.join(root, dir[:i])):
                        i += 1
                    newDir = dir[:i]
                    os.rename(os.path.join(root, dir), os.path.join(root, newDir))

    for root, dirs, files in os.walk(IMAGE_FOLDER_PATH):
        for file in files:
            if file.endswith('.dcm'):
                filePath = winapi_path(os.path.join(root, file))
                fileDirname = os.path.dirname(filePath)
                if dirname == fileDirname:
                    dicomFilePaths[-1].append(filePath)
                else:
                    dicomFilePaths.append([filePath])
                    dicomFileDirs.append(fileDirname)
                dirname = os.path.dirname(filePath)

    for i in range(len(dicomFilePaths)):
        if i % 10 == 0 or i == len(dicomFilePaths)-1:
            print(f'{round((i + 1) / len(dicomFilePaths) * 100, 2)}%')
        file = pydicom.dcmread(dicomFilePaths[i][0], force=True)
        # print(getattr(file, 'PatientID', None))
        headers = getDicomHeaders(file)
        traits = {
            "Patient ID":
            getattr(file, 'PatientID', None),
            "Patient's Sex":
            getattr(file, 'PatientSex', None),
            "Patient's Age":
            getattr(file, 'PatientAge', None),
            "Patient's Birth Date":
            getattr(file, 'PatientBirthDate', None),
            "Patient's Weight":
            getattr(file, 'PatientWeight', None),
            "Institution Name":
            getattr(file, 'InstitutionName', None),
            "Referring Physician's Name":
            getattr(file, 'ReferringPhysicianName', None),
            "Operator's Name":
            getattr(file, 'OperatorsName', None),
            "Study Date":
            getattr(file, 'StudyDate', None),
            "Study Time":
            getattr(file, 'StudyTime', None),
            "Modality":
            getattr(file, 'Modality', None),
            "Series Description":
            getattr(file, 'SeriesDescription', None),
            "Dimensions":
            np.array(getattr(file, 'pixel_array', None)).shape,
        }
        for key in headers.keys():
            if key not in dicomFileHeaderKeys:
                dicomFileHeaderKeys.append(key)
        dicomFileTraits.append(traits)
        dicomFileHeaders.append(headers)

        fileModality = getattr(file, 'Modality', None)
        filePatientID = getattr(file, 'PatientID', None)

        if QUERY_FILE_PATH:
            filters = pd.read_csv(QUERY_FILE_PATH)
            if fileModality and filePatientID:
                if 'Modality' in filters.columns and (filters['PatientId']
                                                      == filePatientID).any():
                    if fileModality != 'RTSTRUCT' and fileModality != filters.loc[
                            filters['PatientId'] == filePatientID].at[
                                0, 'Modality']:
                        for fileToDelete in dicomFilePaths[i]:
                            os.remove(fileToDelete)
                        os.rmdir(dicomFileDirs[i])
                        print(dicomFileDirs[i])

        if fileModality == 'RTSTRUCT':
            seriesInstanceUID = headers['30060010']['Value'][0]['30060012'][
                'Value'][0]['30060014']['Value'][0]['0020000E']['Value'][0]
            labelInstanceUIDs.append(seriesInstanceUID)

            labelPaths.append(dicomFilePaths[i][0])

    for i in range(len(dicomFileDirs)):
        if i % 10 == 0 or i == len(dicomFileDirs)-1:
            print(f'{round((i + 1) / len(dicomFileDirs) * 100, 2)}%')
        file = pydicom.dcmread(dicomFilePaths[i][0], force=True)
        fileModality = getattr(file, 'Modality', None)
        seriesInstanceUID = getDicomHeaders(file)['0020000E']['Value'][0]
        if fileModality != 'RTSTRUCT':
            if seriesInstanceUID in labelInstanceUIDs:
                seriesPaths.append(dicomFileDirs[i])
                seriesInstanceUIDs.append(seriesInstanceUID)
            # else:
            #     if DELETE_UNMATCHED_SERIES == 'True' and fileModality != 'CT':
            #         for fileToDelete in dicomFilePaths[i]:
            #             os.remove(fileToDelete)
            #         os.rmdir(dicomFileDirs[i])

    labelInstanceUIDs, labelPaths = sortParallelLists(
        labelInstanceUIDs, labelPaths)
    seriesInstanceUIDs, seriesPaths = sortParallelLists(
        seriesInstanceUIDs, seriesPaths)

    if len(dicomFilePaths) > 0:
        with open('data/' + ATTRIBUTE_FILE_NAME, 'w', encoding='UTF8',
                  newline='') as f:
            writer = csv.DictWriter(f, fieldnames=dicomFileTraits[0].keys())
            writer.writeheader()
            writer.writerows(dicomFileTraits)
        
        if SAVE_JSON:
            with open('data/' + HEADERS_FILE_NAME, 'w') as f:
                json.dump(dicomFileHeaders, f)

    for i in range(len(dicomFileDirs)):
        if i % 10 == 0 or i == len(dicomFileDirs)-1:
            print(f'{round((i+1)/len(dicomFileDirs)*100, 2)}%')
        dicomDir = dicomFileDirs[i]
        niftiDir = dicomFileDirs[i].replace("DICOM", "NIFTI")
        if not os.path.exists(niftiDir):
            os.makedirs(niftiDir)

            if len(dicomFilePaths[i]) > 1:
                file = pydicom.dcmread(dicomFilePaths[i][0], force=True)
                fileModality = getattr(file, 'Modality', None)
                seriesInstanceUID = getDicomHeaders(file)['0020000E']['Value'][0]

                ## Converting DICOM series to NIFTI files feature and deleting unmatched series is removed.
                # if [0x054, 0x0016] in file:  # only convert files that have SUV values
                #     if DELETE_UNMATCHED_SERIES == 'True':
                #         if fileModality == 'CT' or seriesInstanceUID in labelInstanceUIDs:
                #             dicomToNifti(file, dicomDir, niftiDir)
                #     else:
                #         dicomToNifti(file, dicomDir, niftiDir)

    for i in range(min([len(labelPaths), len(seriesPaths)])):
        if i % 10 == 0 or i == len(dicomFileDirs)-1:
            print(f'{round((i+1)/min([len(labelPaths), len(seriesPaths)])*100, 2)}%')
        if len(labelInstanceUIDs) != len(seriesInstanceUIDs):
            j = 0
            if len(labelInstanceUIDs) < len(seriesInstanceUIDs):
                while labelInstanceUIDs[i] != seriesInstanceUIDs[i+j] and (i + j) < len(seriesInstanceUIDs):
                    j += 1
                try:
                    buildMasks(pydicom.dcmread(labelPaths[i], force=True), seriesPaths[i+j], labelPaths[i])
                except:
                    print('Failed to build mask for label: ', labelPaths[i])
            else:
                while seriesInstanceUIDs[i] != labelInstanceUIDs[i+j] and (i + j) < len(labelInstanceUIDs):
                    j += 1
                try:
                    buildMasks(pydicom.dcmread(labelPaths[i+j], force=True), seriesPaths[i], labelPaths[i+j])
                except:
                    print('Failed to build mask for label: ', labelPaths[i+j])
        else:
            try:
                buildMasks(pydicom.dcmread(labelPaths[i], force=True), seriesPaths[i], labelPaths[i])
            except:
                print('Failed to build mask for label: ', labelPaths[i])

    if RESTRUCTURE_FOLDERS:
        for root, dirs, files in os.walk(IMAGE_FOLDER_PATH):
            for file in files:
                if 'NIFTI' in root:
                    os.replace(os.path.join(root, file), os.path.join(root.split('NIFTI')[0], file))

    if len(dicomFileDirs) > 0:
        print('Done!', f'Created {len(dicomFileDirs)} NIFTI files')
    else:
        print('No files in directory to convert. Check if your query is valid!')


if __name__ == '__main__':

    convertFiles()