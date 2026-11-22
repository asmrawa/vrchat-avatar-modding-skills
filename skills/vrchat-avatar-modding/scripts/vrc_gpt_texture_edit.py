"""Request one PNG atlas edit from an OpenAI-compatible Images API."""

import argparse
import base64
from http.client import HTTPException
import json
import os
from pathlib import Path
import re
import secrets
import struct
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import build_opener, HTTPRedirectHandler, Request


class EditError(ValueError):
    """A diagnostic safe to display without request data."""


class NoRedirect(HTTPRedirectHandler):
    """Keep credentials on the configured endpoint and downloads on their supplied URL."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def png_info(data):
    if (len(data) < 45 or data[:16] != b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
            or data[-12:] != b"\x00\x00\x00\x00IEND\xaeB\x60\x82"):
        raise EditError("expected a complete PNG file")
    return struct.unpack(">II", data[16:24]), data[25]


def multipart(fields, files):
    boundary = secrets.token_hex(24)
    body = bytearray()
    for name, value in fields.items():
        header = f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n'
        body.extend(header.encode("ascii") + value.encode("utf-8") + b"\r\n")
    for name, data in files.items():
        header = (f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"; '
                  f'filename="{name}.png"\r\nContent-Type: image/png\r\n\r\n')
        body.extend(header.encode("ascii") + data + b"\r\n")
    body.extend(f"--{boundary}--\r\n".encode("ascii"))
    return bytes(body), f"multipart/form-data; boundary={boundary}"


def edit_url(base):
    url = urlsplit(base)
    local_http = url.scheme == "http" and url.hostname in {"localhost", "127.0.0.1", "::1"}
    if (not url.hostname or url.username is not None or url.password is not None
            or url.query or url.fragment or not (url.scheme == "https" or local_http)):
        raise EditError("set OPENAI_BASE_URL to the HTTPS API base including /v1 (HTTP allowed on loopback)")
    return base.rstrip("/") + "/images/edits"


def read_result(payload, opener):
    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, list) or not data or not isinstance(data[0], dict):
        raise EditError("image response has no result")
    item = data[0]
    if isinstance(item.get("b64_json"), str) and item["b64_json"]:
        result = base64.b64decode(item["b64_json"], validate=True)
    else:
        if not isinstance(item.get("url"), str):
            raise EditError("image response contains no base64 data or download URL")
        url = urlsplit(item["url"])
        if url.scheme != "https" or not url.hostname or url.username is not None or url.password is not None:
            raise EditError("image response requires base64 PNG data or an HTTPS download URL")
        # A signed download URL supplies its own access; never forward the API key.
        with opener.open(Request(url.geturl()), timeout=120) as response:
            result = response.read()
    png_info(result)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True, type=Path, help="Original full PNG atlas.")
    parser.add_argument("--mask", type=Path, help="Same-size PNG with transparent pixels to edit.")
    prompts = parser.add_mutually_exclusive_group(required=True)
    prompts.add_argument("--prompt")
    prompts.add_argument("--prompt-file", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--size", default="auto", help="auto or provider-supported WIDTHxHEIGHT.")
    parser.add_argument("--quality", choices=("auto", "low", "medium", "high"), default="auto")
    parser.add_argument("--model", default=os.environ.get("OPENAI_IMAGE_MODEL"))
    parser.add_argument("--dry-run", action="store_true", help="Validate local inputs without a key, request or output.")
    args = parser.parse_args(argv)
    try:
        if args.output.suffix.lower() != ".png" or not args.output.parent.is_dir():
            raise EditError("choose a .png output in an existing directory")
        if os.path.lexists(args.output):
            raise EditError("output already exists")
        prompt = args.prompt_file.read_text(encoding="utf-8-sig") if args.prompt_file else args.prompt
        if not prompt.strip() or not (args.model or "").strip():
            raise EditError("provide a nonempty prompt and --model or OPENAI_IMAGE_MODEL")
        if args.size != "auto" and not re.fullmatch(r"[1-9]\d*x[1-9]\d*", args.size):
            raise EditError("--size must be auto or WIDTHxHEIGHT")
        files = {"image": args.image.read_bytes()}
        size, _ = png_info(files["image"])
        if args.mask:
            files["mask"] = args.mask.read_bytes()
            mask_size, kind = png_info(files["mask"])
            if mask_size != size or kind not in {4, 6}:
                raise EditError("API mask must be an LA or RGBA PNG matching the original dimensions")
        base = os.environ.get("OPENAI_BASE_URL", "")
        if args.dry_run:
            if base:
                edit_url(base)
            print(f"Dry run passed: source {size[0]}x{size[1]}, mask={'mask' in files}.")
            return 0
        url = edit_url(base)
        key = os.environ.get("OPENAI_API_KEY", "")
        if not key:
            raise EditError("set OPENAI_API_KEY in the environment")
        fields = dict(prompt=prompt, model=args.model, size=args.size, quality=args.quality)
        body, content_type = multipart(fields, files)
        request = Request(url, data=body, headers={"Authorization": f"Bearer {key}", "Content-Type": content_type})
        opener = build_opener(NoRedirect())
        with opener.open(request, timeout=300) as response:
            payload = json.load(response)
        image = read_result(payload, opener)
        with args.output.open("xb") as stream:
            try:
                stream.write(image)
                stream.flush()
            except OSError:
                stream.close()
                args.output.unlink()
                raise
    except HTTPError as error:
        print(f"Image request failed (HTTP {error.code}).", file=sys.stderr)
        return 1
    except EditError as error:
        print(f"Image edit failed: {error}", file=sys.stderr)
        return 1
    except (URLError, OSError, HTTPException, ValueError, TypeError) as error:
        # Exceptions from providers and libraries may contain URLs, headers, or request data.
        print(f"Image edit failed ({type(error).__name__}). Check inputs, environment, and response format.", file=sys.stderr)
        return 1
    print("Saved PNG preview.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
