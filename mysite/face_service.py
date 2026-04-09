from __future__ import annotations

import base64
import os
from dataclasses import dataclass
from pathlib import Path
from threading import Lock

import cv2
import numpy as np

from .local_face_analysis_service import get_local_face_analysis_service
from .pokemon_service import get_pokemon_service

class FaceServiceError(RuntimeError):
    """Raised when face analysis cannot be completed."""


@dataclass
class MatchResult:
    name: str | None
    score: float
    bbox: list[int]
    keypoints: list[list[int]]


class InsightFaceService:
    """Thin wrapper around InsightFace for detection and identification."""

    def __init__(
        self,
        known_faces_dir: Path,
        *,
        det_size: tuple[int, int] = (640, 640),
        recognition_threshold: float = 0.35,
    ) -> None:
        self.known_faces_dir = known_faces_dir
        self.det_size = det_size
        self.recognition_threshold = recognition_threshold
        self._app = None
        self._lock = Lock()

    def _load_dependencies(self):
        try:
            from insightface.app import FaceAnalysis  # type: ignore
        except ImportError as exc:
            raise FaceServiceError(
                "insightface が見つかりません。`.venv` を有効化して "
                "`pip install onnxruntime insightface` を実行してください。"
            ) from exc
        return FaceAnalysis

    def _get_app(self):
        if self._app is not None:
            return self._app

        with self._lock:
            if self._app is not None:
                return self._app

            FaceAnalysis = self._load_dependencies()
            app = FaceAnalysis()
            try:
                app.prepare(ctx_id=0, det_size=self.det_size)
            except Exception:
                app.prepare(ctx_id=-1, det_size=self.det_size)
            self._app = app
            return self._app

    def _iter_known_face_images(self):
        if not self.known_faces_dir.exists():
            return

        for person_dir in sorted(self.known_faces_dir.iterdir()):
            if not person_dir.is_dir():
                continue
            for image_path in sorted(person_dir.iterdir()):
                if image_path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
                    continue
                yield person_dir.name, image_path

    def build_known_face_db(self) -> tuple[np.ndarray, list[str]]:
        app = self._get_app()
        names: list[str] = []
        embeddings: list[np.ndarray] = []

        for person_name, image_path in self._iter_known_face_images() or []:
            image = cv2.imread(str(image_path))
            if image is None:
                continue
            faces = app.get(np.array(image))
            if not faces:
                continue
            embeddings.append(faces[0].embedding.astype(np.float32))
            names.append(person_name)

        if not embeddings:
            raise FaceServiceError(
                "登録顔データがありません。`known_faces/<人物名>/画像.jpg` の形で追加してください。"
            )

        matrix = np.stack(embeddings, axis=0)
        matrix = self._normalize_embeddings(matrix)
        return matrix, names

    @staticmethod
    def _normalize_embeddings(embeddings: np.ndarray) -> np.ndarray:
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms = np.clip(norms, 1e-12, None)
        return embeddings / norms

    def _predict_names(
        self,
        known_embeddings: np.ndarray,
        known_names: list[str],
        unknown_embeddings: np.ndarray,
    ) -> list[tuple[str | None, float]]:
        normalized_unknown = self._normalize_embeddings(unknown_embeddings)
        predictions: list[tuple[str | None, float]] = []

        for emb in normalized_unknown:
            scores = known_embeddings @ emb.T
            best_index = int(np.argmax(scores))
            best_score = float(scores[best_index])
            name = known_names[best_index] if best_score >= self.recognition_threshold else None
            predictions.append((name, best_score))

        return predictions

    @staticmethod
    def _draw_results(image: np.ndarray, faces, predictions) -> np.ndarray:
        output = image.copy()
        for face, (name, score) in zip(faces, predictions):
            bbox = face.bbox.astype(int)
            cv2.rectangle(output, (bbox[0], bbox[1]), (bbox[2], bbox[3]), (0, 160, 255), 2)

            if getattr(face, "kps", None) is not None:
                for x, y in face.kps.astype(int):
                    cv2.circle(output, (x, y), 2, (34, 197, 94), 2)

            label = f"{name or 'Unknown'} {score:.3f}"
            cv2.putText(
                output,
                label,
                (bbox[0], max(18, bbox[1] - 10)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (255, 255, 255),
                2,
                cv2.LINE_AA,
            )
        return output

    @staticmethod
    def _encode_image(image: np.ndarray) -> str:
        ok, encoded = cv2.imencode(".jpg", image)
        if not ok:
            raise FaceServiceError("結果画像のエンコードに失敗しました。")
        return base64.b64encode(encoded.tobytes()).decode("ascii")

    def analyze(self, image_bytes: bytes, *, feature_mode: str = "pokemon") -> dict:
        if not image_bytes:
            raise FaceServiceError("画像データが空です。")

        buffer = np.frombuffer(image_bytes, dtype=np.uint8)
        image = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
        if image is None:
            raise FaceServiceError("画像を読み込めませんでした。JPEG/PNG を送ってください。")

        app = self._get_app()
        faces = app.get(np.array(image))
        known_embeddings, known_names = self.build_known_face_db()

        if not faces:
            return {
                "face_count": 0,
                "matches": [],
                "feature_mode": feature_mode,
                "auxiliary_result": None,
                "annotated_image_base64": self._encode_image(image),
            }

        unknown_embeddings = np.stack(
            [face.embedding.astype(np.float32) for face in faces],
            axis=0,
        )
        predictions = self._predict_names(known_embeddings, known_names, unknown_embeddings)
        annotated_image = self._draw_results(image, faces, predictions)

        matches = []
        for face, (name, score) in zip(faces, predictions):
            keypoints = []
            if getattr(face, "kps", None) is not None:
                keypoints = face.kps.astype(int).tolist()
            matches.append(
                MatchResult(
                    name=name,
                    score=score,
                    bbox=face.bbox.astype(int).tolist(),
                    keypoints=keypoints,
                ).__dict__
            )

        primary_index = max(
            range(len(matches)),
            key=lambda index: (matches[index]["bbox"][2] - matches[index]["bbox"][0])
            * (matches[index]["bbox"][3] - matches[index]["bbox"][1]),
        )
        primary_face = faces[primary_index]
        auxiliary_result = self._build_auxiliary_result(
            feature_mode=feature_mode,
            image=image,
            face_count=len(matches),
            image_shape=image.shape,
            primary_face=primary_face,
            primary_match=matches[primary_index],
        )

        return {
            "face_count": len(matches),
            "matches": matches,
            "feature_mode": feature_mode,
            "auxiliary_result": auxiliary_result,
            "annotated_image_base64": self._encode_image(annotated_image),
        }

    def _build_auxiliary_result(
        self,
        *,
        feature_mode: str,
        image: np.ndarray,
        face_count: int,
        image_shape,
        primary_face,
        primary_match: dict,
    ) -> dict | None:
        if feature_mode == "local-face-analysis":
            result = get_local_face_analysis_service().analyze(
                image=image,
                primary_face=primary_face,
                primary_match=primary_match,
                face_count=face_count,
            )
            result["kind"] = "local-face-analysis"
            return result

        pokemon_match = get_pokemon_service().recommend(
            age=getattr(primary_face, "age", None),
            bbox=primary_match["bbox"],
            image_shape=image_shape,
            matched_name=primary_match["name"],
        )
        if pokemon_match is None:
            return None
        pokemon_match["kind"] = "pokemon"
        return pokemon_match


def get_default_face_service() -> InsightFaceService:
    base_dir = Path(__file__).resolve().parent.parent
    known_faces_dir = Path(os.environ.get("KNOWN_FACES_DIR", base_dir / "known_faces"))
    return InsightFaceService(known_faces_dir=known_faces_dir)
