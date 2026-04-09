from __future__ import annotations

import math

import cv2
import numpy as np


class LocalFaceAnalysisService:
    def analyze(
        self,
        *,
        image: np.ndarray,
        primary_face,
        primary_match: dict,
        face_count: int,
    ) -> dict:
        bbox = [int(value) for value in primary_match["bbox"]]
        crop = self._crop_face(image=image, bbox=bbox)
        image_height, image_width = image.shape[:2]
        face_width = max(1, bbox[2] - bbox[0])
        face_height = max(1, bbox[3] - bbox[1])
        face_area_ratio = (face_width * face_height) / max(1, image_width * image_height)
        face_ratio = face_width / face_height

        keypoints = []
        if getattr(primary_face, "kps", None) is not None:
            keypoints = primary_face.kps.astype(float).tolist()

        return {
            "face_count": face_count,
            "primary_face": {
                "estimated_age": self._optional_int(getattr(primary_face, "age", None)),
                "estimated_gender": self._normalize_gender(getattr(primary_face, "gender", None)),
                "match_name": primary_match.get("name") or "Unknown",
                "match_score": round(float(primary_match.get("score", 0.0)), 3),
                "face_ratio": round(face_ratio, 3),
                "face_area_ratio": round(face_area_ratio * 100, 2),
                "brightness": self._measure_brightness(crop),
                "sharpness": self._measure_sharpness(crop),
                "eye_balance": self._measure_eye_balance(keypoints),
                "mouth_balance": self._measure_mouth_balance(keypoints),
                "tilt": self._measure_tilt(keypoints),
            },
            "summary": self._build_summary(
                age=self._optional_int(getattr(primary_face, "age", None)),
                gender=self._normalize_gender(getattr(primary_face, "gender", None)),
                face_ratio=face_ratio,
                face_area_ratio=face_area_ratio,
                brightness=self._measure_brightness(crop),
                sharpness=self._measure_sharpness(crop),
            ),
        }

    @staticmethod
    def _crop_face(*, image: np.ndarray, bbox: list[int]) -> np.ndarray:
        height, width = image.shape[:2]
        x1 = max(0, min(width, bbox[0]))
        y1 = max(0, min(height, bbox[1]))
        x2 = max(x1 + 1, min(width, bbox[2]))
        y2 = max(y1 + 1, min(height, bbox[3]))
        return image[y1:y2, x1:x2]

    @staticmethod
    def _optional_int(value) -> int | None:
        if value is None:
            return None
        try:
            return int(round(float(value)))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _normalize_gender(value) -> str | None:
        if value is None:
            return None
        raw = str(value).strip().lower()
        mapping = {
            "0": "女性寄り",
            "1": "男性寄り",
            "female": "女性寄り",
            "male": "男性寄り",
            "f": "女性寄り",
            "m": "男性寄り",
        }
        return mapping.get(raw, str(value))

    @staticmethod
    def _measure_brightness(crop: np.ndarray) -> float:
        if crop.size == 0:
            return 0.0
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        return round(float(np.mean(gray)), 1)

    @staticmethod
    def _measure_sharpness(crop: np.ndarray) -> float:
        if crop.size == 0:
            return 0.0
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        return round(float(cv2.Laplacian(gray, cv2.CV_64F).var()), 1)

    @staticmethod
    def _measure_eye_balance(keypoints: list[list[float]]) -> float | None:
        if len(keypoints) < 2:
            return None
        left_eye, right_eye = keypoints[0], keypoints[1]
        return round(abs(float(left_eye[1]) - float(right_eye[1])), 1)

    @staticmethod
    def _measure_mouth_balance(keypoints: list[list[float]]) -> float | None:
        if len(keypoints) < 5:
            return None
        left_mouth, right_mouth = keypoints[3], keypoints[4]
        return round(abs(float(left_mouth[1]) - float(right_mouth[1])), 1)

    @staticmethod
    def _measure_tilt(keypoints: list[list[float]]) -> float | None:
        if len(keypoints) < 2:
            return None
        left_eye, right_eye = keypoints[0], keypoints[1]
        dy = float(right_eye[1]) - float(left_eye[1])
        dx = max(1e-6, float(right_eye[0]) - float(left_eye[0]))
        return round(math.degrees(math.atan2(dy, dx)), 1)

    @staticmethod
    def _build_summary(
        *,
        age: int | None,
        gender: str | None,
        face_ratio: float,
        face_area_ratio: float,
        brightness: float,
        sharpness: float,
    ) -> str:
        parts: list[str] = []
        if age is not None:
            parts.append(f"推定年齢は {age} 歳前後です")
        if gender:
            parts.append(f"見た目傾向は {gender} です")

        shape = "丸顔寄り" if face_ratio >= 0.92 else "シャープ寄り" if face_ratio <= 0.76 else "バランス型"
        parts.append(f"顔立ちは {shape} に見えます")

        size = "存在感が強め" if face_area_ratio >= 0.18 else "標準的"
        parts.append(f"写り方は {size} です")

        light = "明るめ" if brightness >= 150 else "落ち着いた明るさ"
        detail = "くっきり" if sharpness >= 300 else "やわらかめ"
        parts.append(f"画像の印象は {light}・{detail} です")
        return " / ".join(parts)


def get_local_face_analysis_service() -> LocalFaceAnalysisService:
    return LocalFaceAnalysisService()
