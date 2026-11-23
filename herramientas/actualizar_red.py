#!/usr/bin/env python3
"""Arma la foto semanal y el data.json de la versión pública de la Red de Proyectos.

Uso:
  python3 actualizar_red.py <carpeta_export> <salida_data.json> [--foto <salida_foto.json>]

<carpeta_export> tiene las colecciones exportadas de la base como
proyectos/*.json, aprendizajes/*.json e historial/*.json (un archivo por documento).
Las fotos de cada proyecto se publican solo si su archivo ya está en img/<id>.<ext> del repo.
"""
import datetime, glob, json, os, sys

AR = datetime.timezone(datetime.timedelta(hours=-3))


def cargar(base, coleccion):
    docs = []
    for ruta in sorted(glob.glob(os.path.join(base, coleccion, "*.json"))):
        with open(ruta, encoding="utf-8") as f:
            d = json.load(f)
        if isinstance(d, dict) and isinstance(d.get("data"), dict):
            d = d["data"]
        d = {k: v for k, v in d.items() if not k.startswith("__") and k != "version"}
        d["id"] = os.path.splitext(os.path.basename(ruta))[0]
        docs.append(d)
    return docs


def cifras(proyectos, aprendizajes):
    vivos = [p for p in proyectos if p.get("estado", "activo") != "pausa"]
    tareas = [t for p in vivos for t in p.get("tareas", [])]
    hechas = sum(1 for t in tareas if t.get("hecha"))
    total = len(tareas)
    return {"pct": round(hechas * 100 / total) if total else 0, "hechas": hechas,
            "total": total, "aprendizajes": len(aprendizajes)}


def parte_publica(proyectos, aprendizajes):
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pub = [dict(p) for p in proyectos if p.get("publico") is not False]
    ids = {p["id"] for p in pub}
    for p in pub:
        p.pop("publico", None)
        # quién o qué se espera puede tener nombres: no sale en la pública
        p["tareas"] = [{k: v for k, v in t.items() if k not in ("espera", "esperaDesde")} for t in p.get("tareas", [])]
        # solo las fotos que ya están copiadas en img/
        fotos = []
        for f in p.get("fotos", []):
            ruta = "img/%s.%s" % (f.get("id"), f.get("ext", "jpg"))
            if os.path.exists(os.path.join(raiz, ruta)):
                fotos.append({"id": f.get("id"), "ext": f.get("ext", "jpg"), "src": ruta})
        if fotos:
            p["fotos"] = fotos
        else:
            p.pop("fotos", None)
    apr = []
    for a in aprendizajes:
        if a.get("origen") not in ids:
            continue
        a = dict(a)
        a["destinos"] = [d for d in a.get("destinos", []) if d in ids]
        if a["destinos"]:
            apr.append(a)
    return pub, apr


def main():
    base, salida = sys.argv[1], sys.argv[2]
    proyectos = cargar(base, "proyectos")
    aprendizajes = cargar(base, "aprendizajes")
    historial = cargar(base, "historial")
    pub, apr_pub = parte_publica(proyectos, aprendizajes)

    if "--foto" in sys.argv:
        ahora = datetime.datetime.now(AR)
        foto = {"fecha": ahora.date().isoformat(), "n": (ahora.date().toordinal() - 1) // 7,
                **cifras(proyectos, aprendizajes), "publico": cifras(pub, apr_pub)}
        with open(sys.argv[sys.argv.index("--foto") + 1], "w", encoding="utf-8") as f:
            json.dump(foto, f, ensure_ascii=False, indent=1)
        historial = [h for h in historial if h.get("n") != foto["n"]] + [dict(foto, id="s%d" % foto["n"])]

    hist_pub = sorted(({"fecha": h["fecha"], "n": h["n"], **h.get("publico", h)} for h in historial if "n" in h),
                      key=lambda h: h["n"])
    for h in hist_pub:
        h.pop("publico", None)
    datos = {"actualizado": datetime.datetime.now(AR).isoformat(timespec="minutes"),
             "proyectos": pub, "aprendizajes": apr_pub, "historial": hist_pub}
    with open(salida, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=1)
    print("Públicos: %d proyectos, %d aprendizajes, %d semanas" % (len(pub), len(apr_pub), len(hist_pub)))


if __name__ == "__main__":
    main()
