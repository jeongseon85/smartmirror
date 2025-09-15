# personal_color_analysis/detect_face.py

from imutils import face_utils
import numpy as np
import dlib
import cv2

class DetectFace:
    def __init__(self, image_path):
        # res 폴더의 경로를 명시
        predictor_path = 'res/shape_predictor_68_face_landmarks.dat'
        self.detector = dlib.get_frontal_face_detector()
        self.predictor = dlib.shape_predictor(predictor_path)

        self.img = cv2.imread(image_path)
        if self.img is None:
            raise RuntimeError(f"Error: Could not read image from {image_path}")

        self.right_eyebrow = []
        self.left_eyebrow = []
        self.right_eye = []
        self.left_eye = []
        self.left_cheek = []
        self.right_cheek = []

        self.detect_face_part()

    def detect_face_part(self):
        gray = cv2.cvtColor(self.img, cv2.COLOR_BGR2GRAY)
        rects = self.detector(gray, 1)
        if len(rects) == 0:
            raise RuntimeError("No face detected in the image.")

        rect = rects[0]
        shape = self.predictor(gray, rect)
        shape = face_utils.shape_to_np(shape)

        face_parts_indices = face_utils.FACIAL_LANDMARKS_IDXS
        
        # 눈썹, 눈 추출
        self.right_eyebrow = self.extract_face_part(shape[face_parts_indices["right_eyebrow"][0]:face_parts_indices["right_eyebrow"][1]])
        self.left_eyebrow = self.extract_face_part(shape[face_parts_indices["left_eyebrow"][0]:face_parts_indices["left_eyebrow"][1]])
        self.right_eye = self.extract_face_part(shape[face_parts_indices["right_eye"][0]:face_parts_indices["right_eye"][1]])
        self.left_eye = self.extract_face_part(shape[face_parts_indices["left_eye"][0]:face_parts_indices["left_eye"][1]])

        # 뺨 추출
        self.left_cheek = self.img[shape[29][1]:shape[33][1], shape[4][0]:shape[48][0]]
        self.right_cheek = self.img[shape[29][1]:shape[33][1], shape[54][0]:shape[12][0]]

    def extract_face_part(self, face_part_points):
        (x, y, w, h) = cv2.boundingRect(face_part_points)
        crop = self.img[y:y+h, x:x+w].copy() # .copy() 추가
        adj_points = np.array([p - [x, y] for p in face_part_points])
        
        mask = np.zeros((crop.shape[0], crop.shape[1]), dtype=np.uint8)
        cv2.fillConvexPoly(mask, adj_points, 1)
        mask = mask.astype(bool)
        
        # 마스크를 씌우는 대신, 마스크 영역 외부에 투명도(alpha)를 추가
        # 이 코드에서는 마스크가 아닌 직접 [255, 0, 0]으로 채우므로 기존 코드 유지
        crop[np.logical_not(mask)] = [255, 0, 0]
        
        return crop