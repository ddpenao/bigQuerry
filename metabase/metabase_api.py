"""Funciones comunes para hablar con la API de Metabase (solo librería estándar)."""
import getpass
import json
import urllib.error
import urllib.request


class Metabase:
    def __init__(self, url, email, password=None):
        self.url = url.rstrip("/")
        if password is None:
            password = getpass.getpass(f"Contraseña de Metabase para {email}: ")
        sesion = self._pedir("POST", "/api/session", {"username": email, "password": password}, auth=False)
        self.token = sesion["id"]

    def _pedir(self, metodo, ruta, cuerpo=None, auth=True):
        datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
        req = urllib.request.Request(self.url + ruta, data=datos, method=metodo)
        req.add_header("Content-Type", "application/json")
        if auth:
            req.add_header("X-Metabase-Session", self.token)
        try:
            with urllib.request.urlopen(req) as r:
                texto = r.read().decode()
        except urllib.error.HTTPError as e:
            raise SystemExit(f"Error {e.code} en {metodo} {ruta}: {e.read().decode()[:500]}")
        return json.loads(texto) if texto else None

    def get(self, ruta):
        return self._pedir("GET", ruta)

    def post(self, ruta, cuerpo):
        return self._pedir("POST", ruta, cuerpo)

    def put(self, ruta, cuerpo):
        return self._pedir("PUT", ruta, cuerpo)
