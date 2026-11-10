import json
from pathlib import Path
from struct import pack
from zlib import compress
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parent
PACKS = ("FieldArms_BP", "FieldArms_RP")
OUTPUT = ROOT / "FieldArms.mcaddon"
TEXTURE = ROOT / "FieldArms_RP/textures/items/fieldarms_pistol.png"


def validate_pack(pack_dir: Path) -> dict:
    manifest_path = pack_dir / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Missing pack manifest: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not manifest.get("modules") or not manifest.get("header", {}).get("uuid"):
        raise ValueError(f"Invalid pack manifest: {manifest_path}")
    if not any(path.is_file() for path in pack_dir.rglob("*")):
        raise ValueError(f"Pack has no files: {pack_dir}")
    return manifest


def create_pistol_texture(path: Path) -> None:
    width = height = 32
    pixels = [(0, 0, 0, 0)] * (width * height)
    outline = (28, 31, 34, 255)
    steel = (118, 128, 132, 255)
    steel_light = (177, 185, 184, 255)
    steel_dark = (69, 77, 81, 255)
    grip = (112, 63, 38, 255)
    grip_light = (155, 91, 51, 255)
    accent = (196, 73, 43, 255)

    def rect(x0: int, y0: int, x1: int, y1: int, color: tuple[int, int, int, int]) -> None:
        for y in range(y0, y1):
            for x in range(x0, x1):
                pixels[y * width + x] = color

    rect(5, 9, 27, 16, outline)
    rect(8, 7, 24, 9, outline)
    rect(11, 16, 20, 19, outline)
    rect(10, 18, 20, 21, outline)
    rect(9, 20, 19, 23, outline)
    rect(8, 22, 18, 25, outline)
    rect(7, 24, 16, 27, outline)
    rect(4, 10, 24, 15, steel)
    rect(8, 8, 23, 9, steel_dark)
    rect(7, 11, 22, 12, steel_light)
    rect(24, 11, 29, 14, steel_dark)
    rect(23, 12, 28, 13, steel)
    rect(12, 16, 18, 18, steel_light)
    rect(11, 18, 18, 20, grip)
    rect(10, 20, 17, 22, grip_light)
    rect(9, 22, 16, 24, grip)
    rect(8, 24, 15, 26, grip_light)
    rect(12, 19, 14, 20, accent)
    rect(16, 15, 18, 17, outline)

    raw = b"".join(
        b"\x00" + bytes(channel for pixel in pixels[y * width:(y + 1) * width] for channel in pixel)
        for y in range(height)
    )

    def chunk(kind: bytes, data: bytes) -> bytes:
        import binascii

        body = kind + data
        return pack(">I", len(data)) + body + pack(">I", binascii.crc32(body) & 0xFFFFFFFF)

    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", pack(">2I5B", width, height, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", compress(raw))
        + chunk(b"IEND", b"")
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(png)


def main() -> None:
    manifests = {name: validate_pack(ROOT / name) for name in PACKS}
    behavior_dependencies = manifests["FieldArms_BP"].get("dependencies", [])
    resource_uuid = manifests["FieldArms_RP"]["header"]["uuid"]
    if not any(dependency.get("uuid") == resource_uuid for dependency in behavior_dependencies):
        raise ValueError("Behavior pack manifest does not depend on the resource pack")

    create_pistol_texture(TEXTURE)
    temporary_output = OUTPUT.with_suffix(".mcaddon.tmp")
    try:
        with ZipFile(temporary_output, "w", compression=ZIP_DEFLATED) as archive:
            for name in PACKS:
                pack_dir = ROOT / name
                for path in sorted(pack_dir.rglob("*")):
                    if path.is_file():
                        archive.write(path, path.relative_to(ROOT).as_posix())
        temporary_output.replace(OUTPUT)
    finally:
        temporary_output.unlink(missing_ok=True)

    print(f"Created Minecraft Bedrock add-on: {OUTPUT}")


if __name__ == "__main__":
    main()
