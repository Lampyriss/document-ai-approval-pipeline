# Image Preprocessing Module for Handwriting OCR
# ปรับปรุงภาพก่อนส่งให้ OCR เพื่อให้อ่านลายมือได้ดีขึ้น

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
import io
import logging

logger = logging.getLogger(__name__)


class ImagePreprocessor:
    """
    Preprocess images to improve OCR accuracy, especially for handwriting
    
    เทคนิคที่ใช้:
    1. Contrast Enhancement - เพิ่ม contrast ให้ลายมือชัดขึ้น
    2. Sharpening - ทำให้ขอบตัวอักษรคมขึ้น
    3. Binarization - แปลงเป็นขาวดำ
    4. Noise Reduction - ลด noise
    5. Deskew - ปรับความเอียง (optional)
    """
    
    def __init__(self, 
                 contrast_factor: float = 1.5,
                 brightness_factor: float = 1.1,
                 sharpness_factor: float = 2.0,
                 denoise: bool = True,
                 binarize: bool = False,
                 binarize_threshold: int = 128):
        """
        Initialize preprocessor with settings
        
        Args:
            contrast_factor: 1.0 = no change, >1 = more contrast
            brightness_factor: 1.0 = no change, >1 = brighter
            sharpness_factor: 1.0 = no change, >1 = sharper
            denoise: Apply median filter to reduce noise
            binarize: Convert to black & white
            binarize_threshold: Threshold for binarization (0-255)
        """
        self.contrast_factor = contrast_factor
        self.brightness_factor = brightness_factor
        self.sharpness_factor = sharpness_factor
        self.denoise = denoise
        self.binarize = binarize
        self.binarize_threshold = binarize_threshold
    
    def preprocess(self, image: np.ndarray) -> np.ndarray:
        """
        Apply all preprocessing steps to image
        
        Args:
            image: numpy array (RGB or grayscale)
            
        Returns:
            Preprocessed image as numpy array
        """
        try:
            # Convert numpy array to PIL Image
            if len(image.shape) == 2:
                # Grayscale
                pil_img = Image.fromarray(image, mode='L')
            else:
                # RGB/RGBA
                if image.shape[2] == 4:
                    # RGBA -> RGB
                    pil_img = Image.fromarray(image).convert('RGB')
                else:
                    pil_img = Image.fromarray(image)
            
            # 1. Enhance Contrast
            if self.contrast_factor != 1.0:
                enhancer = ImageEnhance.Contrast(pil_img)
                pil_img = enhancer.enhance(self.contrast_factor)
            
            # 2. Enhance Brightness
            if self.brightness_factor != 1.0:
                enhancer = ImageEnhance.Brightness(pil_img)
                pil_img = enhancer.enhance(self.brightness_factor)
            
            # 3. Sharpen
            if self.sharpness_factor != 1.0:
                enhancer = ImageEnhance.Sharpness(pil_img)
                pil_img = enhancer.enhance(self.sharpness_factor)
            
            # 4. Denoise (Median filter)
            if self.denoise:
                pil_img = pil_img.filter(ImageFilter.MedianFilter(size=3))
            
            # 5. Binarize (optional - can help with some documents)
            if self.binarize:
                # Convert to grayscale first
                gray = pil_img.convert('L')
                # Apply threshold
                pil_img = gray.point(lambda x: 255 if x > self.binarize_threshold else 0, mode='1')
                pil_img = pil_img.convert('RGB')
            
            # Convert back to numpy array
            return np.array(pil_img)
            
        except Exception as e:
            logger.warning(f"Preprocessing failed: {e}, returning original image")
            return image
    
    def preprocess_for_handwriting(self, image: np.ndarray) -> np.ndarray:
        """
        Special preprocessing optimized for handwritten Thai text
        
        Uses gentler settings to avoid over-processing
        """
        try:
            pil_img = Image.fromarray(image)
            
            # Convert to RGB if needed
            if pil_img.mode != 'RGB':
                pil_img = pil_img.convert('RGB')
            
            # 1. Gentle contrast boost
            enhancer = ImageEnhance.Contrast(pil_img)
            pil_img = enhancer.enhance(1.3)
            
            # 2. Slight brightness increase
            enhancer = ImageEnhance.Brightness(pil_img)
            pil_img = enhancer.enhance(1.08)
            
            # 3. Moderate sharpening
            enhancer = ImageEnhance.Sharpness(pil_img)
            pil_img = enhancer.enhance(1.4)
            
            # 4. Light denoise only
            # Skip heavy filtering that can blur handwriting
            
            return np.array(pil_img)
            
        except Exception as e:
            logger.warning(f"Handwriting preprocessing failed: {e}")
            return image


class AdaptivePreprocessor:
    """
    Automatically detect and apply best preprocessing based on image analysis
    """
    
    def __init__(self):
        self.standard = ImagePreprocessor()
        self.handwriting = ImagePreprocessor(
            contrast_factor=1.8,
            brightness_factor=1.15,
            sharpness_factor=2.5,
            denoise=True
        )
    
    def analyze_image(self, image: np.ndarray) -> dict:
        """
        Analyze image characteristics
        
        Returns:
            dict with analysis results
        """
        try:
            # Convert to grayscale for analysis
            if len(image.shape) == 3:
                gray = np.mean(image, axis=2)
            else:
                gray = image
            
            # Calculate statistics
            mean_brightness = np.mean(gray)
            std_brightness = np.std(gray)
            
            # Estimate if image has handwriting (high variance in local regions)
            # This is a simple heuristic
            has_handwriting = std_brightness > 50
            
            # Check if image is too dark or too bright
            is_dark = mean_brightness < 100
            is_bright = mean_brightness > 200
            
            return {
                "mean_brightness": mean_brightness,
                "std_brightness": std_brightness,
                "has_handwriting": has_handwriting,
                "is_dark": is_dark,
                "is_bright": is_bright
            }
        except Exception:
            return {"has_handwriting": False, "is_dark": False, "is_bright": False}
    
    def preprocess(self, image: np.ndarray, force_handwriting: bool = False) -> np.ndarray:
        """
        Automatically choose and apply best preprocessing
        
        Args:
            image: Input image
            force_handwriting: Force handwriting mode
            
        Returns:
            Preprocessed image
        """
        analysis = self.analyze_image(image)
        
        if force_handwriting or analysis.get("has_handwriting", False):
            logger.info("Using handwriting preprocessing mode")
            return self.handwriting.preprocess_for_handwriting(image)
        else:
            logger.info("Using standard preprocessing mode")
            return self.standard.preprocess(image)


# Preset configurations
PRESETS = {
    "standard": {
        "contrast_factor": 1.2,
        "brightness_factor": 1.05,
        "sharpness_factor": 1.3,
        "denoise": True,
        "binarize": False
    },
    "handwriting": {
        "contrast_factor": 1.4,
        "brightness_factor": 1.1,
        "sharpness_factor": 1.5,
        "denoise": True,
        "binarize": False
    },
    "handwriting_aggressive": {
        "contrast_factor": 1.8,
        "brightness_factor": 1.2,
        "sharpness_factor": 2.0,
        "denoise": True,
        "binarize": True,
        "binarize_threshold": 140
    },
    "faded_document": {
        "contrast_factor": 1.6,
        "brightness_factor": 1.25,
        "sharpness_factor": 1.4,
        "denoise": False,
        "binarize": False
    },
    "high_quality_scan": {
        "contrast_factor": 1.1,
        "brightness_factor": 1.0,
        "sharpness_factor": 1.1,
        "denoise": False,
        "binarize": False
    }
}


def get_preprocessor(preset: str = "standard") -> ImagePreprocessor:
    """
    Get preprocessor with preset configuration
    
    Args:
        preset: One of "standard", "handwriting", "handwriting_aggressive", 
                "faded_document", "high_quality_scan"
    """
    config = PRESETS.get(preset, PRESETS["standard"])
    return ImagePreprocessor(**config)


# Singleton instances
_adaptive_preprocessor = None

def get_adaptive_preprocessor() -> AdaptivePreprocessor:
    """Get singleton adaptive preprocessor"""
    global _adaptive_preprocessor
    if _adaptive_preprocessor is None:
        _adaptive_preprocessor = AdaptivePreprocessor()
    return _adaptive_preprocessor
