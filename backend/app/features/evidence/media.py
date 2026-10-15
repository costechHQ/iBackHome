"""Client-safe copies of photos: the same picture with no EXIF metadata.

A photo's EXIF can carry the phone's make and model, serial numbers, the owner's name and the
photographer's exact GPS track. Supervisors, contractors and ops see the original; clients only ever
get this stripped copy (spec: "personal EXIF data is stripped from what clients see").
"""

import io

from PIL import Image, ImageOps

from app.features.evidence import storage

CLIENT_PREFIX = "evidence-client/"


def strip_exif(data: bytes) -> bytes:
    """The photo re-encoded as a JPEG with every EXIF tag removed. Raises ValueError if unreadable."""
    try:
        with Image.open(io.BytesIO(data)) as opened:
            upright = ImageOps.exif_transpose(opened)  # apply the rotation first, then drop the tag
            out = io.BytesIO()
            upright.convert("RGB").save(out, "JPEG", quality=92)  # no exif= argument: nothing is carried over
            return out.getvalue()
    except Exception as exc:  # PIL raises many types for a corrupt image
        raise ValueError("unreadable image") from exc


def client_copy_key(storage_key: str) -> str:
    """Where the stripped copy of `evidence/<project>/<id>.jpg` lives."""
    return CLIENT_PREFIX + storage_key.removeprefix("evidence/")


def client_copy_url(storage_key: str) -> str:
    """A 15-minute URL for the stripped copy, creating the copy the first time it is asked for."""
    key = client_copy_key(storage_key)
    if storage.head_object(key) is None:
        original = storage.read_object(storage_key)
        if original is None:
            raise FileNotFoundError(storage_key)
        storage.write_object(key, strip_exif(original), "image/jpeg")
    return storage.presign_read(key)
