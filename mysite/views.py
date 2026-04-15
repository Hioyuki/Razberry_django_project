from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from django.http import JsonResponse, StreamingHttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST


def _get_face_service_objects():
    # Delay heavy imports so the home page can still boot on constrained hosts.
    from .face_service import FaceServiceError, get_default_face_service

    return FaceServiceError, get_default_face_service


@require_GET
def home(request):
    return render(request, "index.html")


@csrf_exempt
@require_POST
def analyze_face(request):
    upload = request.FILES.get("image")
    feature_mode = request.POST.get("feature_mode", "pokemon")
    if upload is None:
        return JsonResponse({"error": "画像ファイル `image` を送ってください。"}, status=400)

    FaceServiceError, get_default_face_service = _get_face_service_objects()
    service = get_default_face_service()
    try:
        result = service.analyze(upload.read(), feature_mode=feature_mode)
    except FaceServiceError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    except Exception as exc:
        return JsonResponse(
            {"error": f"顔検出処理で予期しないエラーが発生しました: {exc}"},
            status=500,
        )

    return JsonResponse(result)


@csrf_exempt
@require_POST
def capture_pi_camera(request):
    FaceServiceError, get_default_face_service = _get_face_service_objects()
    service = get_default_face_service()
    feature_mode = request.POST.get("feature_mode", "pokemon")

    try:
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temp_file:
            output_path = Path(temp_file.name)

        command = [
            "rpicam-jpeg",
            "--immediate",
            "--nopreview",
            "--width",
            "1280",
            "--height",
            "720",
            "-o",
            str(output_path),
        ]
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )

        if completed.returncode != 0:
            error_text = (completed.stderr or completed.stdout or "").strip()
            raise FaceServiceError(
                "Raspberry Pi カメラで撮影できませんでした。"
                + (f" 詳細: {error_text}" if error_text else "")
            )

        image_bytes = output_path.read_bytes()
        result = service.analyze(image_bytes, feature_mode=feature_mode)
    except FaceServiceError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    except Exception as exc:
        return JsonResponse(
            {"error": f"ラズパイカメラ撮影で予期しないエラーが発生しました: {exc}"},
            status=500,
        )
    finally:
        if "output_path" in locals() and output_path.exists():
            output_path.unlink(missing_ok=True)

    return JsonResponse(result)


def _pi_camera_mjpeg_stream():
    command = [
        "rpicam-vid",
        "--nopreview",
        "--timeout",
        "0",
        "--width",
        "960",
        "--height",
        "540",
        "--framerate",
        "15",
        "--codec",
        "mjpeg",
        "-o",
        "-",
    ]
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        bufsize=0,
    )

    buffer = bytearray()
    try:
        while True:
            if process.stdout is None:
                break
            chunk = process.stdout.read(4096)
            if not chunk:
                break
            buffer.extend(chunk)

            while True:
                start = buffer.find(b"\xff\xd8")
                end = buffer.find(b"\xff\xd9", start + 2 if start != -1 else 0)
                if start == -1 or end == -1:
                    if start > 0:
                        del buffer[:start]
                    break

                frame = bytes(buffer[start : end + 2])
                del buffer[: end + 2]
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n"
                    b"Content-Length: " + str(len(frame)).encode("ascii") + b"\r\n\r\n"
                    + frame
                    + b"\r\n"
                )
    finally:
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()


@require_GET
def pi_camera_stream(request):
    response = StreamingHttpResponse(
        _pi_camera_mjpeg_stream(),
        content_type="multipart/x-mixed-replace; boundary=frame",
    )
    response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return response
