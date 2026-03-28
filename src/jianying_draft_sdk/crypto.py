from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

try:
    from Cryptodome.Cipher import AES
except ImportError:
    from Crypto.Cipher import AES


KEYIV_PATTERN_N_BETWEEN = (3, 9, 9, 3, 3, 8, 3, 6, 9, 6, 24)
TARGET_FILES = ("draft_content.json", "draft_meta_info.json")
_B64_RE = re.compile(rb"^[A-Za-z0-9+/=\s]+$")


@dataclass
class OfflineCryptoResult:
    file_name: str
    input_path: str
    output_path: str
    plaintext_len: int
    plaintext_sha256: str
    key_iv: str
    payload_sha256: str


@dataclass
class DraftFileData:
    file_name: str
    source_path: str
    key_iv: str
    plaintext_text: str
    data: Any


@dataclass
class DraftBundle:
    draft_root: str
    files: dict[str, DraftFileData]


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def compact_b64_text(text: str) -> str:
    return re.sub(r"\s+", "", text)


def looks_like_base64_text(data: bytes) -> bool:
    compact = re.sub(rb"\s+", b"", data)
    return bool(compact) and len(compact) % 4 == 0 and bool(_B64_RE.match(compact))


def deinterleave_keyiv(raw_b64_text: str) -> tuple[str, str]:
    s = compact_b64_text(raw_b64_text)
    pos = 0
    key_chunks: list[str] = []
    new_parts: list[str] = []
    for n_len in KEYIV_PATTERN_N_BETWEEN:
        key_chunks.append(s[pos:pos + 4])
        pos += 4
        new_parts.append(s[pos:pos + n_len])
        pos += n_len
    key_chunks.append(s[pos:pos + 4])
    pos += 4
    new_parts.append(s[pos:])

    key_iv = "".join(key_chunks)
    new_input = "".join(new_parts)
    if len(key_iv) != 48:
        raise ValueError(f"extracted keyIv length != 48: {len(key_iv)}")
    if len(new_input) % 4 != 0:
        raise ValueError(f"restored newInput length is not multiple of 4: {len(new_input)}")
    if not _B64_RE.match(new_input.encode("ascii")):
        raise ValueError("restored newInput is not valid base64 text")
    return key_iv, new_input


def interleave_keyiv(key_iv: str, new_input: str) -> str:
    if len(key_iv) != 48:
        raise ValueError(f"keyIv length must be 48, got {len(key_iv)}")
    if len(new_input) < sum(KEYIV_PATTERN_N_BETWEEN):
        raise ValueError("newInput is too short for the known interleave pattern")
    parts: list[str] = []
    key_pos = 0
    new_pos = 0
    for n_len in KEYIV_PATTERN_N_BETWEEN:
        parts.append(key_iv[key_pos:key_pos + 4])
        key_pos += 4
        parts.append(new_input[new_pos:new_pos + n_len])
        new_pos += n_len
    parts.append(key_iv[key_pos:key_pos + 4])
    parts.append(new_input[new_pos:])
    return "".join(parts)


def decrypt_jianying_text(raw_text: str) -> tuple[bytes, str, str]:
    key_iv, new_input = deinterleave_keyiv(raw_text)
    payload = base64.b64decode(new_input, validate=True)
    if len(payload) < 17:
        raise ValueError("decoded ciphertext payload is too short")
    key = key_iv[:32].encode("utf-8")
    nonce = key_iv[32:48].encode("utf-8")
    ct = payload[:-16]
    tag = payload[-16:]
    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
    plaintext = cipher.decrypt_and_verify(ct, tag)
    return plaintext, key_iv, new_input


def encrypt_jianying_text(plaintext: bytes, key_iv: str) -> tuple[str, str]:
    key = key_iv[:32].encode("utf-8")
    nonce = key_iv[32:48].encode("utf-8")
    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)
    ct, tag = cipher.encrypt_and_digest(plaintext)
    new_input = base64.b64encode(ct + tag).decode("ascii")
    return interleave_keyiv(key_iv, new_input), new_input


def write_plaintext(output_path: Path, plaintext: bytes, pretty: bool) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if pretty:
        obj = json.loads(plaintext.decode("utf-8"))
        output_path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        output_path.write_bytes(plaintext)


def decrypt_jianying_file(
    input_path: str | Path,
    output_path: str | Path,
    *,
    pretty: bool = False,
    keyiv_path: str | Path | None = None,
    newinput_path: str | Path | None = None,
) -> OfflineCryptoResult:
    input_file = Path(input_path).resolve()
    output_file = Path(output_path).resolve()
    raw_text = input_file.read_text(encoding="utf-8").strip()
    plaintext, key_iv, new_input = decrypt_jianying_text(raw_text)
    write_plaintext(output_file, plaintext, pretty=pretty)
    if keyiv_path:
        Path(keyiv_path).resolve().write_text(key_iv, encoding="utf-8")
    if newinput_path:
        Path(newinput_path).resolve().write_text(new_input, encoding="ascii")
    payload = base64.b64decode(new_input, validate=True)
    return OfflineCryptoResult(
        file_name=input_file.name,
        input_path=str(input_file),
        output_path=str(output_file),
        plaintext_len=len(plaintext),
        plaintext_sha256=sha256_hex(plaintext),
        key_iv=key_iv,
        payload_sha256=sha256_hex(payload),
    )


def encrypt_jianying_file(
    input_path: str | Path,
    output_path: str | Path,
    *,
    keyiv: str | None = None,
    keyiv_path: str | Path | None = None,
    dump_newinput: str | Path | None = None,
) -> dict[str, Any]:
    plain_file = Path(input_path).resolve()
    output_file = Path(output_path).resolve()
    if keyiv is None:
        if keyiv_path is None:
            raise ValueError("either keyiv or keyiv_path is required")
        keyiv = Path(keyiv_path).resolve().read_text(encoding="utf-8").strip()
    plaintext = plain_file.read_bytes()
    raw_text, new_input = encrypt_jianying_text(plaintext, keyiv)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(raw_text, encoding="utf-8")
    if dump_newinput:
        Path(dump_newinput).resolve().write_text(new_input, encoding="ascii")
    payload = base64.b64decode(new_input, validate=True)
    return {
        "input": str(plain_file),
        "output": str(output_file),
        "raw_text_len": len(raw_text),
        "payload_b64_len": len(new_input),
        "plaintext_sha256": sha256_hex(plaintext),
        "payload_sha256": sha256_hex(payload),
        "key_iv": keyiv,
    }


def decrypt_draft_directory(
    draft_root: str | Path,
    out_dir: str | Path,
    *,
    pretty: bool = True,
) -> dict[str, Any]:
    root = Path(draft_root).resolve()
    output_root = Path(out_dir).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    results: list[OfflineCryptoResult] = []
    for file_name in TARGET_FILES:
        input_file = root / file_name
        if not input_file.exists():
            continue
        stem = input_file.stem
        results.append(
            decrypt_jianying_file(
                input_file,
                output_root / f"{stem}.plain.json",
                pretty=pretty,
                keyiv_path=output_root / f"{stem}.keyiv.txt",
                newinput_path=output_root / f"{stem}.newinput.txt",
            )
        )
    if not results:
        raise FileNotFoundError(f"no supported encrypted draft files found under {root}")
    return {"draft_root": str(root), "out_dir": str(output_root), "files": [asdict(item) for item in results]}


def reencrypt_draft_directory(plain_dir: str | Path, out_dir: str | Path) -> dict[str, Any]:
    plain_root = Path(plain_dir).resolve()
    output_root = Path(out_dir).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    files: list[dict[str, Any]] = []
    for target in TARGET_FILES:
        stem = Path(target).stem
        plain_path = plain_root / f"{stem}.plain.json"
        keyiv_path = plain_root / f"{stem}.keyiv.txt"
        if not plain_path.exists() or not keyiv_path.exists():
            continue
        files.append(
            encrypt_jianying_file(
                plain_path,
                output_root / target,
                keyiv_path=keyiv_path,
                dump_newinput=output_root / f"{stem}.newinput.txt",
            )
        )
    if not files:
        raise FileNotFoundError(f"no .plain.json + .keyiv.txt pairs found under {plain_root}")
    return {"plain_dir": str(plain_root), "out_dir": str(output_root), "files": files}


def roundtrip_file(input_path: str | Path, out_dir: str | Path) -> dict[str, Any]:
    input_file = Path(input_path).resolve()
    output_root = Path(out_dir).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    stem = input_file.stem
    raw_text = input_file.read_text(encoding="utf-8").strip()
    plaintext, key_iv, new_input = decrypt_jianying_text(raw_text)
    plain_path = output_root / f"{stem}.plain.json"
    keyiv_path = output_root / f"{stem}.keyiv.txt"
    newinput_path = output_root / f"{stem}.newinput.txt"
    reenc_path = output_root / f"{stem}.reencrypted.json"
    plain_path.write_bytes(plaintext)
    keyiv_path.write_text(key_iv, encoding="utf-8")
    newinput_path.write_text(new_input, encoding="ascii")
    reenc_text, reenc_newinput = encrypt_jianying_text(plaintext, key_iv)
    reenc_path.write_text(reenc_text, encoding="utf-8")
    original_raw = base64.b64decode(new_input, validate=True)
    reencr_raw = base64.b64decode(reenc_newinput, validate=True)
    return {
        "input": str(input_file),
        "plain_path": str(plain_path),
        "keyiv_path": str(keyiv_path),
        "reencrypted_path": str(reenc_path),
        "plaintext_len": len(plaintext),
        "plaintext_sha256": sha256_hex(plaintext),
        "key_iv": key_iv,
        "same_final_text": reenc_text == compact_b64_text(raw_text),
        "same_payload_bytes": original_raw == reencr_raw,
        "original_payload_sha256": sha256_hex(original_raw),
        "reencrypted_payload_sha256": sha256_hex(reencr_raw),
    }


def inspect_file(input_path: str | Path) -> dict[str, Any]:
    file_path = Path(input_path).resolve()
    raw = file_path.read_bytes()
    compact = compact_b64_text(raw.decode("utf-8", errors="ignore"))
    info: dict[str, Any] = {
        "path": str(file_path),
        "size": len(raw),
        "looks_like_base64_text": looks_like_base64_text(raw),
        "compact_len": len(compact),
    }
    try:
        plaintext, key_iv, new_input = decrypt_jianying_text(compact)
        info.update(
            {
                "decryptable": True,
                "key_iv": key_iv,
                "plaintext_len": len(plaintext),
                "plaintext_sha256": sha256_hex(plaintext),
                "payload_sha256": sha256_hex(base64.b64decode(new_input, validate=True)),
            }
        )
    except Exception as exc:
        info.update({"decryptable": False, "error": f"{type(exc).__name__}: {exc}"})
    return info


def _load_single_draft_file(path: Path) -> DraftFileData:
    plaintext, key_iv, _ = decrypt_jianying_text(path.read_text(encoding="utf-8").strip())
    plaintext_text = plaintext.decode("utf-8")
    return DraftFileData(
        file_name=path.name,
        source_path=str(path.resolve()),
        key_iv=key_iv,
        plaintext_text=plaintext_text,
        data=json.loads(plaintext_text),
    )


def load_draft(draft_root: str | Path) -> DraftBundle:
    root = Path(draft_root).resolve()
    files: dict[str, DraftFileData] = {}
    for file_name in TARGET_FILES:
        path = root / file_name
        if path.exists():
            files[file_name] = _load_single_draft_file(path)
    if not files:
        raise FileNotFoundError(f"no supported encrypted draft files found under {root}")
    return DraftBundle(draft_root=str(root), files=files)


def save_draft(
    draft: DraftBundle,
    out_dir: str | Path | None = None,
    *,
    pretty: bool = False,
    ensure_ascii: bool = False,
) -> dict[str, Any]:
    output_root = Path(out_dir if out_dir is not None else draft.draft_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    files: list[dict[str, Any]] = []
    for file_name, item in draft.files.items():
        plaintext_text = json.dumps(item.data, ensure_ascii=ensure_ascii, indent=2 if pretty else None)
        plaintext_bytes = plaintext_text.encode("utf-8")
        raw_text, new_input = encrypt_jianying_text(plaintext_bytes, item.key_iv)
        output_path = output_root / file_name
        output_path.write_text(raw_text, encoding="utf-8")
        (output_root / f"{Path(file_name).stem}.keyiv.txt").write_text(item.key_iv, encoding="utf-8")
        (output_root / f"{Path(file_name).stem}.newinput.txt").write_text(new_input, encoding="ascii")
        files.append(
            {
                "file_name": file_name,
                "output_path": str(output_path),
                "plaintext_sha256": sha256_hex(plaintext_bytes),
                "payload_sha256": sha256_hex(base64.b64decode(new_input, validate=True)),
                "key_iv": item.key_iv,
            }
        )
    return {"draft_root": draft.draft_root, "out_dir": str(output_root), "files": files}


def cmd_decrypt(args: argparse.Namespace) -> int:
    print(
        json.dumps(
            asdict(
                decrypt_jianying_file(
                    args.input,
                    args.output,
                    pretty=args.pretty,
                    keyiv_path=args.dump_keyiv,
                    newinput_path=args.dump_newinput,
                )
            ),
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def cmd_encrypt(args: argparse.Namespace) -> int:
    print(
        json.dumps(
            encrypt_jianying_file(
                args.input,
                args.output,
                keyiv=args.keyiv,
                keyiv_path=args.keyiv_path,
                dump_newinput=args.dump_newinput,
            ),
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def cmd_roundtrip(args: argparse.Namespace) -> int:
    print(json.dumps(roundtrip_file(args.input, args.out_dir), ensure_ascii=False, indent=2))
    return 0


def cmd_decrypt_dir(args: argparse.Namespace) -> int:
    print(json.dumps(decrypt_draft_directory(args.draft_root, args.out_dir, pretty=not args.no_pretty), ensure_ascii=False, indent=2))
    return 0


def cmd_encrypt_dir(args: argparse.Namespace) -> int:
    print(json.dumps(reencrypt_draft_directory(args.plain_dir, args.out_dir), ensure_ascii=False, indent=2))
    return 0


def cmd_inspect(args: argparse.Namespace) -> int:
    print(json.dumps(inspect_file(args.input), ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Single-file offline decrypt/encrypt toolkit for Jianying draft_content.json and draft_meta_info.json"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_dec = sub.add_parser("decrypt", help="Decrypt one encrypted Jianying JSON file")
    p_dec.add_argument("input")
    p_dec.add_argument("output")
    p_dec.add_argument("--pretty", action="store_true")
    p_dec.add_argument("--dump-keyiv")
    p_dec.add_argument("--dump-newinput")
    p_dec.set_defaults(func=cmd_decrypt)

    p_enc = sub.add_parser("encrypt", help="Encrypt one plaintext JSON file back to Jianying format")
    p_enc.add_argument("input")
    p_enc.add_argument("output")
    p_enc.add_argument("--keyiv")
    p_enc.add_argument("--keyiv-path")
    p_enc.add_argument("--dump-newinput")
    p_enc.set_defaults(func=cmd_encrypt)

    p_rt = sub.add_parser("roundtrip", help="Decrypt and immediately re-encrypt one file for verification")
    p_rt.add_argument("input")
    p_rt.add_argument("--out-dir", default="offline_crypto_out")
    p_rt.set_defaults(func=cmd_roundtrip)

    p_dd = sub.add_parser("decrypt-dir", help="Decrypt supported encrypted files under one draft directory")
    p_dd.add_argument("draft_root")
    p_dd.add_argument("--out-dir", default="offline_draft_out")
    p_dd.add_argument("--no-pretty", action="store_true")
    p_dd.set_defaults(func=cmd_decrypt_dir)

    p_ed = sub.add_parser("encrypt-dir", help="Re-encrypt plaintext files produced by decrypt-dir")
    p_ed.add_argument("plain_dir")
    p_ed.add_argument("--out-dir", default="offline_draft_reencrypted")
    p_ed.set_defaults(func=cmd_encrypt_dir)

    p_ins = sub.add_parser("inspect", help="Inspect whether a file matches the Jianying encrypted format")
    p_ins.add_argument("input")
    p_ins.set_defaults(func=cmd_inspect)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
