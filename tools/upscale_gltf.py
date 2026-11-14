#!/usr/bin/env python3
"""upscale_gltf — ingrandisce con Real-ESRGAN le texture di un glTF e ne scrive la copia `*_hd.gltf` (uso personale).

  tools/upscale_gltf.py out/aerei/xfa27_smooth1.gltf [--model realesrgan-x4plus-anime] [--scale 4]

Richiede Real-ESRGAN ncnn-vulkan in ~/Tools/realesrgan (tools/install_upscaler.sh). Le PNG ingrandite stanno accanto al glTF
(`nome_hd.png`), il glTF nuovo punta a quelle. Modello consigliato per texture PS1 (pannelli e linee nette): realesrgan-x4plus-anime
(confronto a vista su XFA-27: meglio di realesrgan-x4plus, che aggiunge grana, e di realesr-animevideov3, piu' sfocato).
Solo libreria standard; esegue il binario locale gia' installato.
"""
import hashlib, json, os, shutil, subprocess, sys

BIN = os.path.expanduser("~/Tools/realesrgan/realesrgan-ncnn-vulkan")


def main():
    a = sys.argv[1:]
    if not a or a[0].startswith("-"):
        print(__doc__); sys.exit(2)
    src = a[0]
    model = a[a.index("--model") + 1] if "--model" in a else "realesrgan-x4plus-anime"
    scale = a[a.index("--scale") + 1] if "--scale" in a else "4"
    if not os.path.exists(BIN):
        sys.exit("Real-ESRGAN non installato: bash tools/install_upscaler.sh")
    d = os.path.dirname(os.path.abspath(src))
    g = json.load(open(src))
    done = {}
    for img in g.get("images", []):
        uri = img["uri"]
        if uri not in done:
            out = os.path.splitext(uri)[0] + "_hd.png"
            # cache per contenuto: pagine identiche (stessa tpage/clut) condivise da piu' modelli si ingrandiscono una volta sola
            h = hashlib.sha1(open(os.path.join(d, uri), "rb").read() + model.encode() + scale.encode()).hexdigest()
            cdir = os.path.join(d, ".hd_cache"); os.makedirs(cdir, exist_ok=True); cf = os.path.join(cdir, h + ".png")
            if os.path.exists(cf):
                shutil.copyfile(cf, os.path.join(d, out)); done[uri] = out; print(f"  {uri} -> {out} (cache)"); img["uri"] = out; continue
            subprocess.run([BIN, "-i", os.path.join(d, uri), "-o", os.path.join(d, out), "-n", model, "-s", scale,
                            "-m", os.path.dirname(BIN) + "/models"], check=True, capture_output=True)
            shutil.copyfile(os.path.join(d, out), cf)
            done[uri] = out
            print(f"  {uri} -> {out}")
        img["uri"] = done[uri]
    dst = os.path.splitext(os.path.abspath(src))[0] + "_hd.gltf"
    json.dump(g, open(dst, "w"))
    print("scritto", dst)


if __name__ == "__main__":
    main()
