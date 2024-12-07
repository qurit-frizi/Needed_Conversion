import os
import numpy as np
import nibabel as nib
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap

def get_MIP(data: np.ndarray, plane: str) -> np.ndarray:
    plane = plane.lower()
    if plane == 'axial':
        mip = data.max(axis=2)  # [X,Y]
    elif plane == 'coronal':
        mip = data.max(axis=1)  # [X,Z]
    elif plane == 'sagittal':
        mip = data.max(axis=0)  # [Y,Z]
    else:
        raise ValueError("Plane must be 'axial', 'coronal', or 'sagittal'.")
    return mip

def enhance_dynamic_range(image: np.ndarray, low_percent=1, high_percent=99) -> np.ndarray:
    """Enhance dynamic range using percentile-based contrast stretching."""
    low_val, high_val = np.percentile(image, (low_percent, high_percent))
    image_clipped = np.clip(image, low_val, high_val)
    image_norm = (image_clipped - low_val) / (high_val - low_val)
    return image_norm

# Paths to your NIfTI files
pet_nifti_file = "/content/drive/MyDrive/maziar_NET/data/DICOM/NIFTI/AB98_PT_20181206.nii.gz"
mask_nifti_file = "/content/drive/MyDrive/maziar_NET/data/DICOM/NIFTI/AB98_RTSTRUCT_20181206_mask.nii.gz"

pet_img = nib.load(pet_nifti_file)
pet_data = pet_img.get_fdata().astype(np.float32)

if os.path.exists(mask_nifti_file):
    mask_img = nib.load(mask_nifti_file)
    mask_data = mask_img.get_fdata().astype(np.float32)
else:
    mask_data = np.array([])

# Generate MIPs
coronal_pet_mip = get_MIP(pet_data, 'coronal')
coronal_mask_mip = get_MIP(mask_data, 'coronal') if mask_data.size > 0 else None

sagittal_pet_mip = get_MIP(pet_data, 'sagittal')
sagittal_mask_mip = get_MIP(mask_data, 'sagittal') if mask_data.size > 0 else None

# Parameters
invert_gray = True
alpha = 0.5
rotate_coronal = True
rotate_sagittal = True

# Enhance dynamic range of the MIPs
coronal_pet_mip = enhance_dynamic_range(coronal_pet_mip)
sagittal_pet_mip = enhance_dynamic_range(sagittal_pet_mip)

# Rotate if needed
if rotate_coronal:
    coronal_pet_mip = np.rot90(coronal_pet_mip, k=1)
    if coronal_mask_mip is not None and coronal_mask_mip.size > 0:
        coronal_mask_mip = np.rot90(coronal_mask_mip, k=1)

if rotate_sagittal:
    sagittal_pet_mip = np.rot90(sagittal_pet_mip, k=1)
    if sagittal_mask_mip is not None and sagittal_mask_mip.size > 0:
        sagittal_mask_mip = np.rot90(sagittal_mask_mip, k=1)

# Prepare the figure
fig, axs = plt.subplots(1, 2, figsize=(12, 6))
cmap_choice = 'gray_r' if invert_gray else 'gray'
red_cmap = ListedColormap([[1, 0, 0, 1]])  # pure red

# Plot Coronal
axs[0].imshow(coronal_pet_mip, cmap=cmap_choice)
axs[0].set_aspect('equal', adjustable='box')
if coronal_mask_mip is not None and coronal_mask_mip.size > 0:
    mask_bin = (coronal_mask_mip > 0).astype(np.float32)
    mask_m = np.ma.masked_where(mask_bin == 0, mask_bin)
    axs[0].imshow(mask_m, cmap=red_cmap, alpha=alpha)
    axs[0].set_title("Coronal MIP (with Mask)", fontsize=14)
else:
    axs[0].set_title("Coronal MIP (No Mask)", fontsize=14)
axs[0].axis('off')

# Plot Sagittal
axs[1].imshow(sagittal_pet_mip, cmap=cmap_choice)
axs[1].set_aspect('equal', adjustable='box')
if sagittal_mask_mip is not None and sagittal_mask_mip.size > 0:
    mask_bin = (sagittal_mask_mip > 0).astype(np.float32)
    mask_m = np.ma.masked_where(mask_bin == 0, mask_bin)
    axs[1].imshow(mask_m, cmap=red_cmap, alpha=alpha)
    axs[1].set_title("Sagittal MIP (with Mask)", fontsize=14)
else:
    axs[1].set_title("Sagittal MIP (No Mask)", fontsize=14)
axs[1].axis('off')

plt.tight_layout()
plt.show()
