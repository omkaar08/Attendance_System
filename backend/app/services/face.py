"""
Face analysis service wrapping InsightFace (ArcFace buffalo_sc).

Singleton pattern with thread-safe lazy initialization so the model is only
loaded once per process.  Image decoding is done with OpenCV; embeddings are
512-dimensional L2-normalised float vectors (ArcFace standard).
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

MODEL_NAME = "buffalo_sc"
MODEL_VERSION = "1.0"
FALLBACK_MODEL_NAME = "opencv_haar_dct"
FALLBACK_MODEL_VERSION = "1.0"
EMBEDDING_DIM = 512
_DET_SCORE_FLOOR = 0.5


@dataclass
class FaceResult:
    embedding: list[float]
    quality_score: float   # normalised detection confidence [0, 1]
    landmarks: dict        # {"left_eye": [x,y], "right_eye": [x,y], ...}
    bbox: list[float]      # [x1, y1, x2, y2]


def decode_image(image_bytes: bytes) -> np.ndarray | None:
    """Decode raw image bytes to a BGR ndarray. Returns None on failure."""
    arr = np.frombuffer(image_bytes, np.uint8)
    return cv2.imdecode(arr, cv2.IMREAD_COLOR)


def _to_normalized_embedding(face_crop: np.ndarray) -> list[float]:
    gray = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY) if face_crop.ndim == 3 else face_crop
    gray = cv2.equalizeHist(gray)
    resized = cv2.resize(gray, (32, 32), interpolation=cv2.INTER_AREA)
    dct = cv2.dct(resized.astype(np.float32) / 255.0)
    embedding = dct[:16, :32].reshape(EMBEDDING_DIM).astype(np.float32)
    embedding -= float(embedding.mean())
    norm = float(np.linalg.norm(embedding))
    if norm > 1e-10:
        embedding /= norm
    return embedding.tolist()


def _estimate_quality(face_crop: np.ndarray, *, image_area: float) -> float:
    gray = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY) if face_crop.ndim == 3 else face_crop
    sharpness = float(cv2.Laplacian(gray, cv2.CV_32F).var())
    sharpness_score = min(sharpness / 250.0, 1.0)
    area_score = min((gray.shape[0] * gray.shape[1]) / max(image_area, 1.0) * 8.0, 1.0)
    return round(max(0.35, min(0.95, 0.4 + (0.3 * area_score) + (0.3 * sharpness_score))), 4)


class FaceAnalyzer:
    """
    Thread-safe singleton that wraps ``insightface.app.FaceAnalysis``.

    Lazy-loads the model on first call to ``get()`` so the server process can
    start without the model being present (useful during CI / schema-only runs).
    """

    _instance: FaceAnalyzer | None = None
    _lock: threading.Lock = threading.Lock()

    # ------------------------------------------------------------------ init

    def __init__(self) -> None:
        self._fa = None
        self._cascade: cv2.CascadeClassifier | None = None
        self.model_name = MODEL_NAME
        self.model_version = MODEL_VERSION

    @classmethod
    def get(cls) -> FaceAnalyzer:
        with cls._lock:
            if cls._instance is None:
                inst = cls()
                inst._load()
                cls._instance = inst
        return cls._instance  # type: ignore[return-value]

    def _load(self) -> None:
        # Deferred import keeps the process startable even if insightface is
        # being installed in the background.
        try:
            from insightface.app import FaceAnalysis  # noqa: PLC0415
        except ModuleNotFoundError:
            self._load_fallback()
            return

        fa = FaceAnalysis(name=MODEL_NAME, providers=["CPUExecutionProvider"])
        fa.prepare(ctx_id=0, det_size=(640, 640))
        self._fa = fa

    def _load_fallback(self) -> None:
        cascade_path = Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
        cascade = cv2.CascadeClassifier(str(cascade_path))
        if cascade.empty():
            raise RuntimeError("Could not load the fallback OpenCV face detector.")

        self._cascade = cascade
        self.model_name = FALLBACK_MODEL_NAME
        self.model_version = FALLBACK_MODEL_VERSION

    # --------------------------------------------------------------- analysis

    def analyze(self, image_bytes: bytes) -> list[FaceResult]:
        """
        Detect and describe all faces in *image_bytes*.

        Returns a list of :class:`FaceResult` sorted by quality (best first).
        Faces with detection score below ``_DET_SCORE_FLOOR`` are dropped.
        """
        img = decode_image(image_bytes)
        if img is None:
            return []

        if self._fa is None:
            return self._analyze_with_fallback(img)

        raw_faces = self._fa.get(img)
        results: list[FaceResult] = []

        for face in raw_faces:
            det_score = float(face.det_score)
            if det_score < _DET_SCORE_FLOOR:
                continue

            embedding: list[float] = face.embedding.tolist()

            landmarks: dict = {}
            if face.kps is not None:
                kps = face.kps.tolist()
                keys = ["left_eye", "right_eye", "nose", "left_mouth", "right_mouth"]
                landmarks = {keys[i]: kps[i] for i in range(min(len(kps), 5))}

            bbox: list[float] = face.bbox.tolist() if face.bbox is not None else []

            results.append(
                FaceResult(
                    embedding=embedding,
                    quality_score=round(min(det_score, 1.0), 4),
                    landmarks=landmarks,
                    bbox=bbox,
                )
            )

        results.sort(key=lambda r: r.quality_score, reverse=True)
        return results

    def _analyze_with_fallback(self, image: np.ndarray) -> list[FaceResult]:
        if self._cascade is None:
            return []

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)
        detections = self._cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(64, 64),
        )

        image_area = float(image.shape[0] * image.shape[1])
        results: list[FaceResult] = []
        for x, y, w, h in detections:
            x1 = max(int(x), 0)
            y1 = max(int(y), 0)
            x2 = min(int(x + w), image.shape[1])
            y2 = min(int(y + h), image.shape[0])
            face_crop = image[y1:y2, x1:x2]
            if face_crop.size == 0:
                continue

            results.append(
                FaceResult(
                    embedding=_to_normalized_embedding(face_crop),
                    quality_score=_estimate_quality(face_crop, image_area=image_area),
                    landmarks={},
                    bbox=[float(x1), float(y1), float(x2), float(y2)],
                )
            )

        results.sort(key=lambda r: r.quality_score, reverse=True)
        return results


# --------------------------------------------------------------------------- #
#  Pure-Python cosine similarity helpers (used when pgvector is unavailable)   #
# --------------------------------------------------------------------------- #

def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity in [0, 1].  Returns 0.0 on zero-norm vectors."""
    va = np.array(a, dtype=np.float32)
    vb = np.array(b, dtype=np.float32)
    norm_a = float(np.linalg.norm(va))
    norm_b = float(np.linalg.norm(vb))
    if norm_a < 1e-10 or norm_b < 1e-10:
        return 0.0
    return float(np.dot(va, vb) / (norm_a * norm_b))
