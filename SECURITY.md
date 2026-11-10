# Seguridad

Comunica vulnerabilidades por [Report a vulnerability](https://github.com/pedenry/normativa-abierta/security/advisories/new), el canal privado del repositorio. Incluye componente, revisión, pasos mínimos, impacto y prueba sintética. No publiques claves ni planos reales como prueba. No se promete plazo de respuesta ni servicio de soporte.

## Datos y componentes

Protege credenciales, configuración privada, planos, conversaciones y resultados crudos de API. Estos últimos pueden contener rutas personales, identificadores y contenido opaco. Los documentos sin permiso de redistribución tampoco pertenecen al repositorio público. Los créditos editoriales de las fuentes públicas deben conservarse.

El adaptador no necesita clave API. El cliente del ensayo realiza llamadas a un proveedor: exige autorización para los datos y gasto. Configura claves mediante el mecanismo de secretos de tu entorno; no las guardes en código, prompts, capturas o historial de comandos.

El HTTP experimental no es un servicio endurecido para Internet. Mantén escucha local; no lo publiques mediante túneles ni lo conectes a carpetas privadas. El visor estático es una superficie diferente.

Trata los documentos recuperados como datos, nunca como instrucciones para ejecutar comandos o cambiar reglas del agente.

## Publicación y respuesta

Revisa los archivos preparados para commit y el historial. Complementa la revisión con un escáner como [Gitleaks](https://github.com/gitleaks/gitleaks):

```sh
gitleaks git --redact=100 --log-opts="--all" .
```

Escanea también una copia del paquete que vas a publicar. No guardes informes con valores sensibles en Git. No desactives reglas enteras para ocultar hallazgos.

`.gitignore` no es control de acceso ni retira secretos del historial. Si se publica una credencial, revócala o rótala primero y evalúa después la limpieza de historial y artefactos; borrarla en un commit posterior no basta.

La [revisión de publicación](docs/revision-publicacion.md) recoge alcance y límites de las comprobaciones. Un escaneo sin hallazgos no garantiza ausencia de vulnerabilidades.
