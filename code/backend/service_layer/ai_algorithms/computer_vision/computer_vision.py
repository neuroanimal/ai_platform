"""
Classic Computer Vision Algorithms - Minimal API wrappers
"""
import numpy as np
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass

try:
    import cv2
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False

try:
    from skimage import feature, filters, morphology
    from skimage.feature import hog
    SKIMAGE_AVAILABLE = True
except ImportError:
    SKIMAGE_AVAILABLE = False

@dataclass
class FilterResult:
    filtered_image: np.ndarray
    metadata: Optional[Dict] = None

@dataclass
class FeatureResult:
    features: np.ndarray
    keypoints: Optional[List] = None
    descriptors: Optional[np.ndarray] = None

@dataclass
class FlowResult:
    flow_vectors: np.ndarray
    magnitude: Optional[np.ndarray] = None
    angle: Optional[np.ndarray] = None

class ComputerVision:
    """Minimal wrappers for classic computer vision algorithms"""
    
    def sobel_filter(self, image: np.ndarray, direction: str = 'both') -> FilterResult:
        """Sobel edge detection filter"""
        if not OPENCV_AVAILABLE and not SKIMAGE_AVAILABLE:
            raise ImportError("opencv-python or scikit-image required")
        
        if len(image.shape) == 3:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if OPENCV_AVAILABLE else np.mean(image, axis=2)
        
        if OPENCV_AVAILABLE:
            if direction == 'x':
                filtered = cv2.Sobel(image, cv2.CV_64F, 1, 0, ksize=3)
            elif direction == 'y':
                filtered = cv2.Sobel(image, cv2.CV_64F, 0, 1, ksize=3)
            else:  # both
                sobelx = cv2.Sobel(image, cv2.CV_64F, 1, 0, ksize=3)
                sobely = cv2.Sobel(image, cv2.CV_64F, 0, 1, ksize=3)
                filtered = np.sqrt(sobelx**2 + sobely**2)
        else:
            if direction == 'x':
                filtered = filters.sobel_h(image)
            elif direction == 'y':
                filtered = filters.sobel_v(image)
            else:  # both
                filtered = filters.sobel(image)
        
        return FilterResult(
            filtered_image=filtered.astype(np.uint8),
            metadata={'direction': direction}
        )
    
    def canny_edge(self, image: np.ndarray, low_threshold: int = 50, 
                   high_threshold: int = 150) -> FilterResult:
        """Canny edge detection"""
        if not OPENCV_AVAILABLE:
            raise ImportError("opencv-python required")
        
        if len(image.shape) == 3:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        edges = cv2.Canny(image, low_threshold, high_threshold)
        
        return FilterResult(
            filtered_image=edges,
            metadata={'low_threshold': low_threshold, 'high_threshold': high_threshold}
        )
    
    def hog_features(self, image: np.ndarray, orientations: int = 9, 
                     pixels_per_cell: Tuple[int, int] = (8, 8),
                     cells_per_block: Tuple[int, int] = (2, 2)) -> FeatureResult:
        """Histogram of Oriented Gradients (HOG) features"""
        if not SKIMAGE_AVAILABLE:
            raise ImportError("scikit-image required")
        
        if len(image.shape) == 3:
            image = np.mean(image, axis=2)
        
        features = hog(
            image,
            orientations=orientations,
            pixels_per_cell=pixels_per_cell,
            cells_per_block=cells_per_block,
            visualize=False
        )
        
        return FeatureResult(
            features=features,
            metadata={
                'orientations': orientations,
                'pixels_per_cell': pixels_per_cell,
                'cells_per_block': cells_per_block
            }
        )
    
    def sift_features(self, image: np.ndarray) -> FeatureResult:
        """SIFT (Scale-Invariant Feature Transform) features"""
        if not OPENCV_AVAILABLE:
            raise ImportError("opencv-python required")
        
        if len(image.shape) == 3:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        try:
            sift = cv2.SIFT_create()
        except AttributeError:
            # Fallback for older OpenCV versions
            sift = cv2.xfeatures2d.SIFT_create()
        
        keypoints, descriptors = sift.detectAndCompute(image, None)
        
        # Convert keypoints to simple format
        kp_list = [(kp.pt[0], kp.pt[1], kp.angle, kp.response) for kp in keypoints]
        
        return FeatureResult(
            features=descriptors if descriptors is not None else np.array([]),
            keypoints=kp_list,
            descriptors=descriptors
        )
    
    def surf_features(self, image: np.ndarray, hessian_threshold: int = 400) -> FeatureResult:
        """SURF (Speeded-Up Robust Features) features"""
        if not OPENCV_AVAILABLE:
            raise ImportError("opencv-python required")
        
        if len(image.shape) == 3:
            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        try:
            surf = cv2.xfeatures2d.SURF_create(hessian_threshold)
            keypoints, descriptors = surf.detectAndCompute(image, None)
            
            # Convert keypoints to simple format
            kp_list = [(kp.pt[0], kp.pt[1], kp.angle, kp.response) for kp in keypoints]
            
            return FeatureResult(
                features=descriptors if descriptors is not None else np.array([]),
                keypoints=kp_list,
                descriptors=descriptors
            )
        except AttributeError:
            # SURF not available in this OpenCV build
            raise ImportError("SURF not available in this OpenCV build")
    
    def lucas_kanade_flow(self, prev_frame: np.ndarray, curr_frame: np.ndarray,
                         points: Optional[np.ndarray] = None) -> FlowResult:
        """Lucas-Kanade optical flow"""
        if not OPENCV_AVAILABLE:
            raise ImportError("opencv-python required")
        
        if len(prev_frame.shape) == 3:
            prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
        else:
            prev_gray = prev_frame
            
        if len(curr_frame.shape) == 3:
            curr_gray = cv2.cvtColor(curr_frame, cv2.COLOR_BGR2GRAY)
        else:
            curr_gray = curr_frame
        
        # If no points provided, detect corners
        if points is None:
            points = cv2.goodFeaturesToTrack(prev_gray, maxCorners=100, 
                                           qualityLevel=0.3, minDistance=7, blockSize=7)
        
        if points is None or len(points) == 0:
            return FlowResult(flow_vectors=np.array([]))
        
        # Calculate optical flow
        lk_params = dict(winSize=(15, 15), maxLevel=2,
                        criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 10, 0.03))
        
        next_points, status, error = cv2.calcOpticalFlowPyrLK(prev_gray, curr_gray, points, None, **lk_params)
        
        # Select good points
        good_new = next_points[status == 1]
        good_old = points[status == 1]
        
        # Calculate flow vectors
        flow_vectors = good_new - good_old
        
        # Calculate magnitude and angle
        magnitude = np.sqrt(flow_vectors[:, 0]**2 + flow_vectors[:, 1]**2)
        angle = np.arctan2(flow_vectors[:, 1], flow_vectors[:, 0])
        
        return FlowResult(
            flow_vectors=flow_vectors,
            magnitude=magnitude,
            angle=angle
        )
    
    def morphological_operations(self, image: np.ndarray, operation: str = 'opening',
                               kernel_size: int = 5, kernel_shape: str = 'ellipse') -> FilterResult:
        """Morphological operations (opening, closing, erosion, dilation)"""
        if not OPENCV_AVAILABLE:
            raise ImportError("opencv-python required")
        
        # Create kernel
        if kernel_shape == 'ellipse':
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
        elif kernel_shape == 'cross':
            kernel = cv2.getStructuringElement(cv2.MORPH_CROSS, (kernel_size, kernel_size))
        else:  # rectangle
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_size, kernel_size))
        
        # Apply operation
        if operation == 'erosion':
            result = cv2.erode(image, kernel, iterations=1)
        elif operation == 'dilation':
            result = cv2.dilate(image, kernel, iterations=1)
        elif operation == 'opening':
            result = cv2.morphologyEx(image, cv2.MORPH_OPEN, kernel)
        elif operation == 'closing':
            result = cv2.morphologyEx(image, cv2.MORPH_CLOSE, kernel)
        elif operation == 'gradient':
            result = cv2.morphologyEx(image, cv2.MORPH_GRADIENT, kernel)
        elif operation == 'tophat':
            result = cv2.morphologyEx(image, cv2.MORPH_TOPHAT, kernel)
        elif operation == 'blackhat':
            result = cv2.morphologyEx(image, cv2.MORPH_BLACKHAT, kernel)
        else:
            raise ValueError(f"Unknown operation: {operation}")
        
        return FilterResult(
            filtered_image=result,
            metadata={
                'operation': operation,
                'kernel_size': kernel_size,
                'kernel_shape': kernel_shape
            }
        )
    
    def gaussian_blur(self, image: np.ndarray, kernel_size: int = 5, sigma: float = 1.0) -> FilterResult:
        """Gaussian blur filter"""
        if not OPENCV_AVAILABLE:
            raise ImportError("opencv-python required")
        
        blurred = cv2.GaussianBlur(image, (kernel_size, kernel_size), sigma)
        
        return FilterResult(
            filtered_image=blurred,
            metadata={'kernel_size': kernel_size, 'sigma': sigma}
        )
    
    def median_filter(self, image: np.ndarray, kernel_size: int = 5) -> FilterResult:
        """Median filter for noise reduction"""
        if not OPENCV_AVAILABLE:
            raise ImportError("opencv-python required")
        
        filtered = cv2.medianBlur(image, kernel_size)
        
        return FilterResult(
            filtered_image=filtered,
            metadata={'kernel_size': kernel_size}
        )
    
    def corner_detection(self, image: np.ndarray, method: str = 'harris', **kwargs) -> FeatureResult:
        """Corner detection (Harris, Shi-Tomasi)"""
        if not OPENCV_AVAILABLE:
            raise ImportError("opencv-python required")
        
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        
        if method == 'harris':
            corners = cv2.cornerHarris(gray, blockSize=2, ksize=3, k=0.04)
            # Find corner coordinates
            corner_coords = np.where(corners > 0.01 * corners.max())
            keypoints = list(zip(corner_coords[1], corner_coords[0]))
            
        elif method == 'shi_tomasi':
            corners = cv2.goodFeaturesToTrack(gray, maxCorners=100, qualityLevel=0.01, 
                                            minDistance=10, **kwargs)
            keypoints = [(int(x), int(y)) for [[x, y]] in corners] if corners is not None else []
            
        else:
            raise ValueError(f"Unknown corner detection method: {method}")
        
        return FeatureResult(
            features=np.array(keypoints),
            keypoints=keypoints
        )