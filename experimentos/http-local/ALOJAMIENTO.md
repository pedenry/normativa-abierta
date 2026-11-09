# Alojamiento público aislado

Servicio read-only para el corpus público. No es el visor oficial ni sustituye a Pages. Escucha en `127.0.0.1` por defecto; `--host 0.0.0.0` se reserva para una plataforma con proxy TLS. El HTTPS lo aporta un túnel o proxy externo. HTTPS temporal verificado y cerrado; Render preparado, no desplegado ni probado allí.

## Arranque local

Desde la raíz del repositorio:

```
python -B experimentos/http-local/servicio_publico.py --port 31118
```

Comprobación:

```
curl http://127.0.0.1:31118/
curl "http://127.0.0.1:31118/buscar?q=rampas"
curl "http://127.0.0.1:31118/leer?doc=DB-SUA-oficial&page=9"
curl http://127.0.0.1:31118/robots.txt
```

Sólo existen `GET /`, `/robots.txt`, `/buscar` y `/leer`. `/estatico` y cualquier otra ruta responden 404. No hay admin, archivos genéricos, APIs externas, secretos ni costes.

## Túnel Quick Tunnel

Se verificó un Quick Tunnel oficial 2026.10.7 con instancia aislada al loopback. La URL temporal usada el 2026-11-09 entre las 01:50:39 y las 01:53:31 se retiró; no está activa y no debe usarse como acceso. Servidor y túnel se detuvieron; el cierre dio un 530 externo. La URL histórica y la evidencia están en el handoff.

Para una prueba nueva, con el servicio anterior en marcha, en otra terminal:

```
cloudflared tunnel --url http://127.0.0.1:31118 --no-autoupdate
```

Es un Quick Tunnel oficial, temporal y sin cuenta. No guarde la URL temporal en el README raíz ni en el visor. Cierre el túnel con `Ctrl+C`; después detenga el servicio.

## Evidencia HTTPS

Sin sesión se validaron 9 controles de rutas y límites, 8 enlaces estables, el 404 histórico sin reemplazo, la edición exacta y texto más SHA; hubo 119 solicitudes 200 y 103 lecturas. El detalle está en el changelog y el handoff.

## Prueba desde ChatGPT/Claude

Añada opcionalmente `prueba=abc123` a la primera petición (alfanumérico, máximo 32, no secreto). El adaptador propaga ese identificador a los `href` internos de `/leer`. Cada solicitud marcada escribe una línea JSON en stdout con ruta, método, id, documento/página si se validaron, status, bytes, SHA256 del cuerpo exacto, tokens cl100k del cuerpo, target y tokens del target. `tokens_target` cuenta el `self.path` completo percent-encoded, pero la query no se registra. No registra consulta, texto, IP ni cookies. Las repeticiones se cuentan por líneas idénticas en el análisis, sin diccionario en memoria.

Las respuestas de `/leer` añaden enlaces estables comprobados en el checkout: PDF físico de Pages con `#page=N`, página HTML real `site/pagina/{slug}__pNNNN.html` y tablas/figuras disponibles. El texto y el ámbito siguen siendo los de `/buscar` y `/leer`.

## Persistencia con HTTPS

Para un servicio persistente, ponga un proxy inverso TLS delante del loopback (Caddy, nginx o un túnel nombrado de Cloudflare). Ejemplo Caddy, con dominio y certificado propios ya resueltos:

```
consulta.example.org {
    reverse_proxy 127.0.0.1:31118
}
```

No se compra ni activa ningún plan y no se ejecuta este despliegue aquí. Cualquier exposición persistente requiere autorización y revisión de logs, cuotas y TLS.

## Render Native Python (candidato)

Preparado, no desplegado ni probado allí. La creación del Web Service Free ya está autorizada; el panel oficial https://dashboard.render.com/login-next, comprobado en Chrome, pide iniciar sesión: ése es el requisito externo, con cuenta propia y sin compartir credenciales, en un workspace sin medio de pago. Alternativa: un host Python ya autorizado con proxy TLS. No hay OAuth a GitHub, secretos, disco persistente ni método de pago.

- Tipo: Web Service Free con URL estable `*.onrender.com`.
- Fuente: Public Git Repository `https://github.com/pedenry/normativa-abierta`, rama `main`.
- Runtime: Python 3.12 (`PYTHON_VERSION=3.12.14`, ya usado localmente).
- Build: `python -m pip install tiktoken==0.14.0`.
- Start: `python -B experimentos/http-local/servicio_publico.py --host 0.0.0.0 --port "$PORT"`.
- Health check: `GET /`.

Render aporta TLS gestionado y bind a `0.0.0.0:$PORT`. Documentación oficial verificada el 2026-11-09: admite Python y fuente de repositorio público, pausa tras 15 min sin tráfico, despertar de ~1 min, 750 h/mes por workspace, cuotas de tráfico/build y suspensión sin método de pago al agotarse; sin SLA de producción. Fuentes: https://render.com/docs/web-services y https://render.com/docs/free. No se proclaman coste ni recursos no comprobados. El acceso del chat no está garantizado: el 403 de la prueba por enlace permanece. Comprobación CLI ya observada por Codex con servidor simulado: loopback por defecto y `0.0.0.0:10000` pasan sin abrir sockets.

## Límites

Target 2048 bytes UTF-8, consulta 400, página de 1 a 4 dígitos, parámetros acotados por ruta, timeout de socket 15 s, cola de escucha 8 y concurrencia 8 a nivel de servidor: al ocuparse se cierra con 503 sin crear hilo, y el permiso se libera en `finally`. El arranque valida 31 `doc.json` con `distribute: true` y todas las referencias del índice dentro de `contenido/`; el índice se conserva completo, sin filtrar. Errores internos se devuelven genéricos y no se registran trazas. No se copian privados, fixtures, rutas privadas ni resultados crudos. Verificado en local: una tabla JSON existente responde 200 y la 9.ª conexión concurrente devuelve 503 con recuperación posterior. La ruta de chat por enlace no quedó probada: ChatGPT reportó 403 y no llegaron peticiones marcadas; Claude no tuvo sesión utilizable. La prueba separada con 5 cuerpos JSON adjuntos (26.329 bytes, 8.723 tokens cl100k) frente a 115.083 de textos completos dio 2/2, sin recuperación por enlace; el 403 permanece y el ahorro en chat por enlace no está comprobado.
