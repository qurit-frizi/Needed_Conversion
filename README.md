## DICOM to NIfTI Conversion with RT-STRUCT and PET SUV Calculation

### Overview
This project provides a Python script to convert DICOM imaging data (including PET and RT-STRUCT DICOM files) into NIfTI format. It also extracts patient and scan attributes into a CSV file, optionally processes PET data to SUV units, and converts RT-STRUCT contours into NIfTI masks. The output is organized into a standardized directory structure that separates NIfTI results for each patient.

Key Features
  PET to NIfTI Conversion: Converts PET DICOM series into .nii.gz volumes.
  SUV Calculation: Automatically computes and applies a Standardized Uptake Value (SUV) scaling factor for PET images.
  RT-STRUCT to NIfTI Masks: Uses rt-utils to extract ROIs from RT-STRUCT files and create corresponding NIfTI mask files.
  Metadata Extraction: Extracts patient- and study-level metadata from the DICOM headers and saves it as attributes.csv.
  Organized Output Structure: For each patient directory, creates a NIFTI folder containing all converted NIfTI files, parallel to the original DICOM folder.


#### Directory Structure
The code expects a directory layout like:
data/
    patientX/
        DICOM/
            ... DICOM files (PET, CT, RT-STRUCT, etc.) ...
    patientY/
        DICOM/
            ... DICOM files ...
            
After processing, the script creates:
data/
    patientX/
        DICOM/
            ... original DICOM files ...
        NIFTI/
            ... converted NIfTI files ...
    patientY/
        ...

Additionally, it produces a attributes.csv file in the data/ directory, summarizing key information from all processed scans.

### Dependencies
Python 3.7+
Pydicom (pip install pydicom)
SimpleITK (pip install SimpleITK)
rt-utils (pip install rt-utils)
NumPy (pip install numpy)
dateutil (pip install python-dateutil)
CSV and JSON (part of Python standard library)
Make sure these packages are installed before running the script.

### Notes and Troubleshooting
  Modality Requirements:
  PET series must be multi-slice to convert successfully. The script checks for Modality == 'PT' to identify PET scans.
  
  RT-STRUCT Requirements:
  Make sure that the RT-STRUCT references a valid DICOM series in the same patient directory, otherwise masks cannot be built.
  
  Directory Names:
  The script attempts to shorten overly long directory names to prevent file system issues.
  
  SUV Calculation:
  If you encounter issues with SUV calculation, ensure that all necessary PET DICOM tags are present. You can comment out the SUV lines if not required.
  
  ### Contributing
Contributions, bug reports, and improvements are welcome. Please open an issue or submit a pull request.

### License
This project is distributed under the MIT License. Feel free to use, modify, and distribute the code.







## NIFTI2RT
This code converts the NIFTI mask file to RT-STRUCT format.
